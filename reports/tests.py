from datetime import datetime, time
from decimal import Decimal
import io
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader
from accounts.models import UserRoleChoices
from catalog.models import Service
from clients.models import Client
from finance.models import PaymentMethodChoices
from finance.services import CashRegisterService, OrderCheckoutService
from inventory.models import (
    Product,
    ProductUnitChoices,
    ProductUsageTypeChoices,
    StockMovementTypeChoices,
)
from inventory.services import StockService
from orders.services import OrderService
from reports.services import DashboardAnalyticsService
from salons.models import Salon, SalonBusinessHours, WeekdayChoices
from scheduling.models import AppointmentStatusChoices, ProfessionalSchedule
from scheduling.services import SchedulingService

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class DashboardAndPrivatePdfReportTests(TestCase):
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
        self.gestor_b = User.objects.create_user(
            email='gestor@beta.com.br',
            password='StrongPassword123!',
            full_name='Gestor Beta',
            role=UserRoleChoices.GESTOR,
            salon=self.salon_b,
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

        self.service_a = Service.objects.create(
            salon=self.salon_a,
            name='Corte Premium',
            duration_minutes=45,
            base_price=Decimal('100.00'),
            default_commission_pct=Decimal('40.00'),
        )
        self.service_a.professionals.add(self.prof_a1, self.prof_a2)

        self.product_a = Product.objects.create(
            salon=self.salon_a,
            name='Finalizador Brilho',
            sku='FIN-01',
            usage_type=ProductUsageTypeChoices.SALE,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('20.00'),
            sale_price=Decimal('50.00'),
            min_stock_alert=3,
        )
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=3,
            actor=self.gestor_a,
        )

        self.client_a = Client.objects.create(
            salon=self.salon_a,
            full_name='Cliente Alpha',
            phone='11977776666',
        )

        # Sessão de caixa no Salão A e no Salão B
        self.session_a = CashRegisterService.open_session(
            salon=self.salon_a,
            opened_by=self.gestor_a,
            opening_balance=Decimal('100.00'),
        )
        self.session_b = CashRegisterService.open_session(
            salon=self.salon_b,
            opened_by=self.gestor_b,
            opening_balance=Decimal('50.00'),
        )

        # Comanda fechada e paga no Salão A (1 serviço R$ 100 + 1 produto R$ 50 - desconto R$ 10 = R$ 140)
        self.order_a = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )
        OrderService.add_service_item(
            order=self.order_a,
            service=self.service_a,
            professional=self.prof_a1,
        )
        OrderService.add_product_item(
            order=self.order_a,
            product=self.product_a,
            quantity=1,
        )
        OrderService.apply_adjustments(
            order=self.order_a,
            discount_amount=Decimal('10.00'),
        )
        OrderCheckoutService.close_and_pay_order(
            salon=self.salon_a,
            order=self.order_a,
            payments=[
                {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('140.00')}
            ],
            actor=self.recep_a,
        )

    def test_dashboard_metrics_and_valid_pdf_downloads_with_pypdf_metadata(self):
        """
        S08-T03 / S08-T04 / RF-011: Dashboard consolida faturamento bruto/líquido, comissões,
        taxa de comparecimento e estoque crítico; PDFs são gerados com ReportLab + PyPDF.
        """
        tz = timezone.get_current_timezone()
        appt_completed = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a1,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 9, 0), tz),
            services=[self.service_a],
        )
        SchedulingService.transition_status(
            appointment=appt_completed,
            new_status=AppointmentStatusChoices.CONFIRMED,
        )
        SchedulingService.transition_status(
            appointment=appt_completed,
            new_status=AppointmentStatusChoices.IN_PROGRESS,
        )
        SchedulingService.transition_status(
            appointment=appt_completed,
            new_status=AppointmentStatusChoices.COMPLETED,
        )

        appt_noshow = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a1,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 11, 0), tz),
            services=[self.service_a],
        )
        SchedulingService.transition_status(
            appointment=appt_noshow,
            new_status=AppointmentStatusChoices.NO_SHOW,
        )

        metrics = DashboardAnalyticsService.get_salon_metrics(salon=self.salon_a)
        self.assertEqual(metrics['gross_revenue'], Decimal('150.00'))
        self.assertEqual(metrics['net_revenue'], Decimal('140.00'))
        self.assertEqual(metrics['commissions_pending_total'], Decimal('40.00'))
        self.assertEqual(metrics['attendance_rate_pct'], Decimal('50.00'))
        self.assertEqual(metrics['no_show_rate_pct'], Decimal('50.00'))
        self.assertEqual(metrics['low_stock_count'], 1)

        # Gestor baixa os 3 PDFs e valida leitura com PyPDF
        self.client.force_login(self.gestor_a)
        for url in (
            reverse('reports:pdf_commissions'),
            reverse('reports:pdf_cash_closing', args=[self.session_a.pk]),
            reverse('reports:pdf_inventory'),
        ):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp['Content-Type'], 'application/pdf')
            reader = PdfReader(io.BytesIO(resp.content))
            self.assertGreaterEqual(len(reader.pages), 1)
            self.assertEqual(reader.metadata.author, 'SPS — Salão Alpha')

    def test_pdf_export_blocks_other_professional_and_cross_tenant_with_403(self):
        """
        S08-T05 / RF-011 / SEC-E Critério de aceite:
        - Profissional pode baixar apenas o próprio PDF de comissões (200 OK).
        - Quando um profissional tenta baixar o PDF de comissões de outro profissional
          ou o relatório de caixa/estoque do salão, recebe 403 Forbidden.
        - Quando um usuário do Salão A tenta baixar PDF de caixa, comissão ou estoque
          do Salão B, recebe 403 Forbidden.
        """
        # 1. Profissional A1 (Ana) baixa o próprio PDF de comissões -> 200 OK
        self.client.force_login(self.prof_a1)
        own_pdf = self.client.get(reverse('reports:pdf_commissions'))
        self.assertEqual(own_pdf.status_code, 200)

        # 2. Profissional A1 tenta baixar PDF de comissões de Carlos (prof_a2) -> 403 Forbidden
        other_prof_pdf = self.client.get(
            f'{reverse("reports:pdf_commissions")}?professional={self.prof_a2.pk}'
        )
        self.assertEqual(other_prof_pdf.status_code, 403)

        # 3. Profissional A1 tenta baixar PDF de Fechamento de Caixa ou de Estoque -> 403 Forbidden
        self.assertEqual(
            self.client.get(
                reverse('reports:pdf_cash_closing', args=[self.session_a.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('reports:pdf_inventory')).status_code,
            403,
        )

        # 4. Gestor do Salão A tenta baixar PDF de Caixa ou Comissão ou Estoque do Salão B -> 403 Forbidden
        self.client.force_login(self.gestor_a)
        self.assertEqual(
            self.client.get(
                reverse('reports:pdf_cash_closing', args=[self.session_b.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                f'{reverse("reports:pdf_commissions")}?professional={self.prof_b.pk}'
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                f'{reverse("reports:pdf_inventory")}?salon={self.salon_b.pk}'
            ).status_code,
            403,
        )
