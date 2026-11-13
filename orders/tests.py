from datetime import datetime, time
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from accounts.models import UserRoleChoices
from catalog.models import Service
from clients.models import Client
from inventory.models import (
    Product,
    ProductUnitChoices,
    ProductUsageTypeChoices,
    StockMovementTypeChoices,
)
from inventory.services import StockService
from orders.forms import OrderProductItemForm, OrderServiceItemForm
from orders.models import ServiceOrder, ServiceOrderStatusChoices
from orders.services import OrderService
from salons.models import Salon, SalonBusinessHours, WeekdayChoices
from scheduling.models import AppointmentStatusChoices, ProfessionalSchedule
from scheduling.services import SchedulingService

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class ServiceOrderAndIsolationTests(TestCase):
    def setUp(self):
        self.salon_a = Salon.objects.create(
            name='Salão Alpha LTDA',
            trade_name='Salão Alpha',
            slug='salao-alpha',
        )
        self.salon_b = Salon.objects.create(
            name='Salão Beta LTDA',
            trade_name='Salão Beta',
            slug='salao-beta',
        )
        SalonBusinessHours.objects.create(
            salon=self.salon_a,
            weekday=WeekdayChoices.MONDAY,
            is_open=True,
            opening_time=time(9, 0),
            closing_time=time(19, 0),
        )

        self.gestor_a = User.objects.create_user(
            email='gestor@alpha.com.br',
            password='StrongPassword123!',
            full_name='Gestor Alpha',
            role=UserRoleChoices.GESTOR,
            salon=self.salon_a,
        )
        self.recep_a = User.objects.create_user(
            email='recep@alpha.com.br',
            password='StrongPassword123!',
            full_name='Recepção Alpha',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon_a,
        )
        self.prof_a1 = User.objects.create_user(
            email='ana@alpha.com.br',
            password='StrongPassword123!',
            full_name='Ana Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_a2 = User.objects.create_user(
            email='carlos@alpha.com.br',
            password='StrongPassword123!',
            full_name='Carlos Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_b = User.objects.create_user(
            email='prof@beta.com.br',
            password='StrongPassword123!',
            full_name='Profissional Beta',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_b,
        )

        ProfessionalSchedule.objects.create(
            salon=self.salon_a,
            professional=self.prof_a1,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

        self.srv_corte = Service.objects.create(
            salon=self.salon_a,
            name='Corte Feminino',
            duration_minutes=45,
            base_price=Decimal('80.00'),
            default_commission_pct=Decimal('40.00'),
        )
        self.srv_corte.professionals.add(self.prof_a1)

        self.srv_hidratacao = Service.objects.create(
            salon=self.salon_a,
            name='Hidratação Profunda',
            duration_minutes=60,
            base_price=Decimal('120.00'),
            default_commission_pct=Decimal('45.00'),
        )
        self.srv_hidratacao.professionals.add(self.prof_a2)

        self.srv_b = Service.objects.create(
            salon=self.salon_b,
            name='Serviço Beta',
            duration_minutes=30,
            base_price=Decimal('50.00'),
        )

        self.product_sale_a = Product.objects.create(
            salon=self.salon_a,
            name='Máscara Capilar Home Care 250g',
            sku='MASC-250',
            usage_type=ProductUsageTypeChoices.SALE,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('25.00'),
            sale_price=Decimal('45.00'),
            min_stock_alert=2,
        )
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=5,
            actor=self.gestor_a,
            reason='Estoque inicial para venda',
        )

        self.product_internal_a = Product.objects.create(
            salon=self.salon_a,
            name='Luvas Descartáveis Caixa',
            sku='LUV-100',
            usage_type=ProductUsageTypeChoices.INTERNAL,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('15.00'),
            sale_price=Decimal('0.00'),
        )
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_internal_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=10,
            actor=self.gestor_a,
        )

        self.product_b = Product.objects.create(
            salon=self.salon_b,
            name='Produto Beta',
            usage_type=ProductUsageTypeChoices.SALE,
            sale_price=Decimal('30.00'),
        )

        self.client_a = Client.objects.create(
            salon=self.salon_a,
            full_name='Juliana Mendes',
            phone='11988881111',
        )

    def test_mixed_order_calculation_multiple_professionals_products_and_discounts(self):
        """
        S06-T03 / S06-T05 / RF-007 Critério de aceite:
        Comanda aberta com 2 serviços (Profissionais A1 e A2) e 1 produto de venda calcula
        corretamente subtotais, descontos por item, desconto/acréscimo geral e total líquido,
        mantendo applied_commission_pct vazio enquanto não for paga no caixa (RF-009).
        """
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
            notes='Atendimento completo + home care',
        )

        # Serviço 1 (Ana): bruto 80.00 - desconto 10.00 = líquido 70.00
        item_srv_1 = OrderService.add_service_item(
            order=order,
            service=self.srv_corte,
            professional=self.prof_a1,
            discount_amount=Decimal('10.00'),
        )
        self.assertEqual(item_srv_1.net_price, Decimal('70.00'))
        self.assertIsNone(item_srv_1.applied_commission_pct)

        # Serviço 2 (Carlos): bruto 120.00 = líquido 120.00
        item_srv_2 = OrderService.add_service_item(
            order=order,
            service=self.srv_hidratacao,
            professional=self.prof_a2,
        )
        self.assertEqual(item_srv_2.net_price, Decimal('120.00'))

        # Produto vendido: 2 unidades * R$ 45.00 = R$ 90.00
        item_prod = OrderService.add_product_item(
            order=order,
            product=self.product_sale_a,
            quantity=2,
        )
        self.assertEqual(item_prod.total_price, Decimal('90.00'))

        order.refresh_from_db()
        self.assertEqual(order.subtotal_services, Decimal('190.00'))
        self.assertEqual(order.subtotal_products, Decimal('90.00'))
        self.assertEqual(order.total_amount, Decimal('280.00'))

        # Aplica desconto geral de R$ 15.00 e acréscimo de R$ 5.00 -> Total = 270.00
        order = OrderService.apply_adjustments(
            order=order,
            discount_amount=Decimal('15.00'),
            surcharge_amount=Decimal('5.00'),
        )
        self.assertEqual(order.total_amount, Decimal('270.00'))

        # Enquanto a comanda apenas está aberta, o estoque físico permanece 5 (baixa ocorre no pagamento - Sprint 07)
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 5)

        # Remover o item de produto recalcula o total para 190 - 15 + 5 = 180.00
        order = OrderService.remove_product_item(order=order, item_id=item_prod.pk)
        self.assertEqual(order.subtotal_products, Decimal('0.00'))
        self.assertEqual(order.total_amount, Decimal('180.00'))

    def test_open_order_from_appointment_and_prevent_duplicate_active_order(self):
        """S06-T03 / RF-007: Abre comanda a partir de Appointment e impede duplicidade ativa."""
        tz = timezone.get_current_timezone()
        appt = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a1,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 10, 0), tz),
            services=[self.srv_corte],
        )

        # Enquanto 'agendado', não permite abrir comanda
        with self.assertRaises(ValidationError):
            OrderService.open_order_from_appointment(
                salon=self.salon_a,
                appointment=appt,
                opened_by=self.recep_a,
            )

        # Transiciona para 'em_atendimento' -> abertura permitida
        SchedulingService.transition_status(
            appointment=appt,
            new_status=AppointmentStatusChoices.IN_PROGRESS,
        )
        order = OrderService.open_order_from_appointment(
            salon=self.salon_a,
            appointment=appt,
            opened_by=self.recep_a,
        )
        self.assertEqual(order.client, self.client_a)
        self.assertEqual(order.service_items.count(), 1)
        self.assertEqual(order.total_amount, Decimal('80.00'))

        # Segunda tentativa para o mesmo agendamento enquanto a comanda está aberta -> rejeitada
        with self.assertRaises(ValidationError):
            OrderService.open_order_from_appointment(
                salon=self.salon_a,
                appointment=appt,
                opened_by=self.recep_a,
            )

        # Se cancelar a primeira comanda, permite abrir nova comanda para o agendamento
        OrderService.cancel_order(order=order, reason='Aberta por engano')
        reopened = OrderService.open_order_from_appointment(
            salon=self.salon_a,
            appointment=appt,
            opened_by=self.recep_a,
        )
        self.assertEqual(reopened.status, ServiceOrderStatusChoices.OPEN)

    def test_order_rejects_internal_only_product_excess_stock_and_disabled_professional(self):
        """RF-007 / RF-008: Valida restrições de produto vendável, saldo disponível e profissional habilitado."""
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )

        # Profissional A1 não está habilitada para Hidratação Profunda (apenas A2)
        with self.assertRaises(ValidationError):
            OrderService.add_service_item(
                order=order,
                service=self.srv_hidratacao,
                professional=self.prof_a1,
            )

        # Produto de consumo interno não pode ser vendido em comanda
        with self.assertRaises(ValidationError):
            OrderService.add_product_item(
                order=order,
                product=self.product_internal_a,
                quantity=1,
            )

        # Quantidade acima do saldo disponível (saldo = 5, tentativa = 6) -> bloqueada
        with self.assertRaises(ValidationError):
            OrderService.add_product_item(
                order=order,
                product=self.product_sale_a,
                quantity=6,
            )

    def test_order_views_permissions_and_cross_tenant_isolation(self):
        """SEC-A, SEC-B, SEC-C, SEC-D: Views de comandas respeitam perfis e isolamento multi-tenant."""
        order_a = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )
        order_b = ServiceOrder.objects.create(salon=self.salon_b)

        # SEC-A: Recepcionista opera comanda do próprio salão via HTTP POST
        self.client.force_login(self.recep_a)
        add_srv_resp = self.client.post(
            reverse('orders:order_add_service', args=[order_a.pk]),
            data={
                'service': self.srv_corte.pk,
                'professional': self.prof_a1.pk,
                'discount_amount': '5.00',
            },
        )
        self.assertEqual(add_srv_resp.status_code, 302)

        add_prod_resp = self.client.post(
            reverse('orders:order_add_product', args=[order_a.pk]),
            data={
                'product': self.product_sale_a.pk,
                'quantity': 1,
            },
        )
        self.assertEqual(add_prod_resp.status_code, 302)

        order_a.refresh_from_db()
        self.assertEqual(order_a.total_amount, Decimal('120.00'))

        # SEC-B: Recepcionista/Gestor do Salão A recebe 404 ao acessar comanda do Salão B
        self.assertEqual(
            self.client.get(reverse('orders:order_detail', args=[order_b.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse('orders:order_cancel', args=[order_b.pk]),
                data={'cancellation_reason': 'Tentativa cross-tenant'},
            ).status_code,
            404,
        )

        # SEC-C: Profissional recebe 403 ao tentar acessar gestão de comandas
        self.client.force_login(self.prof_a1)
        self.assertEqual(
            self.client.get(reverse('orders:order_list')).status_code,
            403,
        )

        # SEC-D: Formulários de item rejeitam serviço, profissional ou produto de outro salão
        cross_srv_form = OrderServiceItemForm(
            data={
                'service': self.srv_b.pk,
                'professional': self.prof_b.pk,
            },
            salon=self.salon_a,
        )
        self.assertFalse(cross_srv_form.is_valid())
        self.assertIn('service', cross_srv_form.errors)
        self.assertIn('professional', cross_srv_form.errors)

        cross_prod_form = OrderProductItemForm(
            data={
                'product': self.product_b.pk,
                'quantity': 1,
            },
            salon=self.salon_a,
        )
        self.assertFalse(cross_prod_form.is_valid())
        self.assertIn('product', cross_prod_form.errors)
