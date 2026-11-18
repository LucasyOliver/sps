from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import UserRoleChoices
from catalog.models import ProfessionalServiceCommission, Service
from clients.models import Client
from finance.models import (
    CashRegisterStatusChoices,
    CashTransactionTypeChoices,
    CommissionEntry,
    CommissionStatusChoices,
    OrderPayment,
    PaymentMethodChoices,
)
from finance.services import (
    CashRegisterService,
    CommissionService,
    OrderCheckoutService,
)
from fiscal.models import (
    FiscalDocumentRecord,
    FiscalDocumentScopeChoices,
    FiscalDocumentStatusChoices,
)
from inventory.models import (
    Product,
    ProductUnitChoices,
    ProductUsageTypeChoices,
    StockMovementTypeChoices,
)
from inventory.services import InsufficientStockError, StockService
from orders.models import ServiceOrder, ServiceOrderStatusChoices
from orders.services import OrderService
from salons.models import Salon, TaxRegimeChoices

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class FinanceCheckoutCommissionAndIsolationTests(TestCase):
    def setUp(self):
        self.salon_a = Salon.objects.create(
            name='Salão Alpha Beleza LTDA',
            trade_name='Salão Alpha',
            slug='salao-alpha',
            cnpj='12.345.678/0001-99',
            municipal_registration='998877',
            tax_regime=TaxRegimeChoices.SIMPLES_NACIONAL,
            is_partner_salon_regime=True,
            ibge_city_code='3550308',
        )
        self.salon_b = Salon.objects.create(
            name='Salão Beta LTDA',
            trade_name='Salão Beta',
            slug='salao-beta',
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
            tax_document='11122233344',
        )
        self.prof_a2 = User.objects.create_user(
            email='carlos@alpha.com.br',
            password='StrongPassword123!',
            full_name='Carlos Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )

        self.srv_corte = Service.objects.create(
            salon=self.salon_a,
            name='Corte + Escova',
            duration_minutes=60,
            base_price=Decimal('100.00'),
            default_commission_pct=Decimal('40.00'),
            lc116_service_code='06.01',
            cnae_code='9602-5/01',
            iss_rate_pct=Decimal('2.00'),
        )
        self.srv_corte.professionals.add(self.prof_a1, self.prof_a2)

        # Regra específica de 50% para Ana no serviço Corte + Escova (RF-003)
        ProfessionalServiceCommission.objects.create(
            salon=self.salon_a,
            professional=self.prof_a1,
            service=self.srv_corte,
            commission_pct=Decimal('50.00'),
        )

        self.srv_hidratacao = Service.objects.create(
            salon=self.salon_a,
            name='Hidratação Capilar',
            duration_minutes=45,
            base_price=Decimal('100.00'),
            default_commission_pct=Decimal('45.00'),
            lc116_service_code='06.01',
        )
        self.srv_hidratacao.professionals.add(self.prof_a2)

        self.product_sale_a = Product.objects.create(
            salon=self.salon_a,
            name='Óleo Reparador de Pontas 60ml',
            sku='OLE-60',
            usage_type=ProductUsageTypeChoices.BOTH,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('20.00'),
            sale_price=Decimal('45.00'),
            min_stock_alert=2,
            ncm_code='33059000',
            cest_code='2002000',
            cfop_default='5102',
        )
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=5,
            actor=self.gestor_a,
            reason='Estoque inicial',
        )

        self.client_a = Client.objects.create(
            salon=self.salon_a,
            full_name='Mariana Costa',
            phone='11999998888',
            cpf_cnpj='12345678901',
            address_city='São Paulo',
            address_state='SP',
            ibge_city_code='3550308',
        )

    def test_no_commission_before_payment_and_checkout_generates_commission_stock_and_fiscal(self):
        """
        S07-T03 / S07-T05 / RF-009 / RF-013 Critérios de aceite:
        - Enquanto a comanda está aberta, 0 comissões existem.
        - Sem caixa aberto, o fechamento é bloqueado.
        - No pagamento integral (dividido Pix + Cartão), gera CommissionEntry com precedência
          correta (50% Ana, 45% Carlos), baixa estoque, lança no caixa e popula FiscalDocumentRecord.
        """
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_corte,
            professional=self.prof_a1,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_hidratacao,
            professional=self.prof_a2,
        )
        OrderService.add_product_item(
            order=order,
            product=self.product_sale_a,
            quantity=1,
        )
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('245.00'))

        # Antes do pagamento: nenhuma comissão, nenhum registro fiscal e estoque intacto em 5
        self.assertEqual(CommissionEntry.objects.for_salon(self.salon_a).count(), 0)
        self.assertEqual(FiscalDocumentRecord.objects.for_salon(self.salon_a).count(), 0)
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 5)

        # Tentativa de fechar sem caixa aberto -> bloqueada
        with self.assertRaises(ValidationError):
            OrderCheckoutService.close_and_pay_order(
                salon=self.salon_a,
                order=order,
                payments=[
                    {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('245.00')}
                ],
                actor=self.recep_a,
            )

        # Abre o caixa diário com R$ 100.00
        cash_session = CashRegisterService.open_session(
            salon=self.salon_a,
            opened_by=self.recep_a,
            opening_balance=Decimal('100.00'),
        )

        # Pagamento com valor divergente do total líquido -> bloqueado
        with self.assertRaises(ValidationError):
            OrderCheckoutService.close_and_pay_order(
                salon=self.salon_a,
                order=order,
                payments=[
                    {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('200.00')}
                ],
                actor=self.recep_a,
            )

        # Fechamento e pagamento misto (Pix R$ 145.00 + Cartão de Crédito R$ 100.00 = R$ 245.00)
        closed_order = OrderCheckoutService.close_and_pay_order(
            salon=self.salon_a,
            order=order,
            payments=[
                {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('145.00')},
                {
                    'payment_method': PaymentMethodChoices.CREDIT_CARD,
                    'amount': Decimal('100.00'),
                },
            ],
            actor=self.recep_a,
        )
        self.assertEqual(closed_order.status, ServiceOrderStatusChoices.CLOSED_PAID)

        # Estoque baixou de 5 para 4 com StockMovement(saida_venda_comanda)
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 4)

        # Caixa esperava 100.00 + 245.00 = 345.00
        cash_session.refresh_from_db()
        self.assertEqual(cash_session.closing_balance_expected, Decimal('345.00'))

        # Comissões geradas: Ana 50% (R$ 50.00) e Carlos 45% (R$ 45.00)
        comm_ana = CommissionEntry.objects.get(order=order, professional=self.prof_a1)
        comm_carlos = CommissionEntry.objects.get(order=order, professional=self.prof_a2)
        self.assertEqual(comm_ana.commission_pct, Decimal('50.00'))
        self.assertEqual(comm_ana.commission_amount, Decimal('50.00'))
        self.assertEqual(comm_ana.status, CommissionStatusChoices.PENDING)
        self.assertEqual(comm_carlos.commission_pct, Decimal('45.00'))
        self.assertEqual(comm_carlos.commission_amount, Decimal('45.00'))

        # FiscalDocumentRecord populado com escopo misto e rateio Salão-Parceiro (RF-013)
        fiscal_rec = FiscalDocumentRecord.objects.get(order=order)
        self.assertEqual(fiscal_rec.document_scope, FiscalDocumentScopeChoices.MIXED)
        self.assertEqual(
            fiscal_rec.status,
            FiscalDocumentStatusChoices.PENDING_FUTURE_INTEGRATION,
        )
        self.assertEqual(fiscal_rec.issuer_snapshot['cnpj'], '12345678000199')
        self.assertEqual(fiscal_rec.customer_snapshot['cpf_cnpj'], '12345678901')
        self.assertEqual(len(fiscal_rec.services_fiscal_payload), 2)
        self.assertEqual(len(fiscal_rec.products_fiscal_payload), 1)
        self.assertEqual(
            fiscal_rec.services_fiscal_payload[0]['partner_salon_split']['partner_quota_amount'],
            '50.00',
        )
        self.assertEqual(
            fiscal_rec.products_fiscal_payload[0]['ncm_code'],
            '33059000',
        )

    def test_insufficient_stock_at_checkout_aborts_entire_atomic_transaction(self):
        """
        S07-T03 / S07-T05 / RF-008 / RNF-002:
        Se o saldo de estoque se tornar insuficiente no momento do fechamento, a transação
        inteira é abortada sem gerar comissão, pagamento, lançamento de caixa ou registro fiscal.
        """
        CashRegisterService.open_session(
            salon=self.salon_a,
            opened_by=self.recep_a,
            opening_balance=Decimal('50.00'),
        )
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_corte,
            professional=self.prof_a1,
        )
        OrderService.add_product_item(
            order=order,
            product=self.product_sale_a,
            quantity=2,
        )
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('190.00'))

        # Outra operação consome 4 unidades antes do pagamento desta comanda -> resta apenas 1 em estoque
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.INTERNAL_OUT,
            quantity=4,
            actor=self.gestor_a,
            reason='Consumo interno concorrente',
        )
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 1)

        with self.assertRaises(InsufficientStockError):
            OrderCheckoutService.close_and_pay_order(
                salon=self.salon_a,
                order=order,
                payments=[
                    {'payment_method': PaymentMethodChoices.CASH, 'amount': Decimal('190.00')}
                ],
                actor=self.recep_a,
            )

        # Rollback atômico completo verificado
        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrderStatusChoices.OPEN)
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 1)
        self.assertEqual(CommissionEntry.objects.filter(order=order).count(), 0)
        self.assertEqual(OrderPayment.objects.filter(order=order).count(), 0)
        self.assertEqual(FiscalDocumentRecord.objects.filter(order=order).count(), 0)

    def test_paid_order_reversal_by_gestor_reverts_cash_commissions_stock_and_fiscal(self):
        """
        S07-T04 / RF-009: Estorno de comanda paga (exclusivo do gestor) reverte atomicamente
        caixa, comissões, saldo de estoque e status do FiscalDocumentRecord.
        """
        cash_session = CashRegisterService.open_session(
            salon=self.salon_a,
            opened_by=self.recep_a,
            opening_balance=Decimal('100.00'),
        )
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.recep_a,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_corte,
            professional=self.prof_a1,
        )
        OrderService.add_product_item(
            order=order,
            product=self.product_sale_a,
            quantity=2,
        )
        order.refresh_from_db()

        OrderCheckoutService.close_and_pay_order(
            salon=self.salon_a,
            order=order,
            payments=[
                {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('190.00')}
            ],
            actor=self.recep_a,
        )
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 3)

        # SEC-C: Recepcionista não pode estornar comanda paga
        with self.assertRaises(PermissionDenied):
            OrderCheckoutService.reverse_paid_order(
                salon=self.salon_a,
                order=order,
                actor=self.recep_a,
                reason='Tentativa não autorizada',
            )

        # Gestor executa estorno via view HTTP POST
        self.client.force_login(self.gestor_a)
        rev_resp = self.client.post(
            reverse('finance:order_reverse', args=[order.pk]),
            data={'reason': 'Lançamento duplicado na recepção'},
        )
        self.assertEqual(rev_resp.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrderStatusChoices.CANCELLED)

        # Estoque restaurado para 5 unidades
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 5)

        # Comissão marcada como estornada
        comm = CommissionEntry.objects.get(order=order)
        self.assertEqual(comm.status, CommissionStatusChoices.REVERSED)
        self.assertIsNotNone(comm.reversed_at)

        # Caixa voltou para o saldo esperado de R$ 100.00
        cash_session.refresh_from_db()
        self.assertEqual(cash_session.closing_balance_expected, Decimal('100.00'))

        # Registro fiscal marcado como cancelado
        fiscal_rec = FiscalDocumentRecord.objects.get(order=order)
        self.assertEqual(fiscal_rec.status, FiscalDocumentStatusChoices.CANCELLED)

    def test_commission_statement_professional_scope_payout_and_cross_tenant_isolation(self):
        """
        SEC-A, SEC-B, SEC-C: Profissional vê apenas as próprias comissões; Gestor realiza
        baixa de pagamento de comissões; isolamento 404 entre salões.
        """
        CashRegisterService.open_session(
            salon=self.salon_a,
            opened_by=self.gestor_a,
            opening_balance=Decimal('0.00'),
        )
        order = OrderService.open_order(
            salon=self.salon_a,
            client=self.client_a,
            opened_by=self.gestor_a,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_corte,
            professional=self.prof_a1,
        )
        OrderService.add_service_item(
            order=order,
            service=self.srv_hidratacao,
            professional=self.prof_a2,
        )
        order.refresh_from_db()
        OrderCheckoutService.close_and_pay_order(
            salon=self.salon_a,
            order=order,
            payments=[
                {'payment_method': PaymentMethodChoices.PIX, 'amount': Decimal('200.00')}
            ],
            actor=self.gestor_a,
        )

        # SEC-C: Profissional Ana vê apenas sua comissão (R$ 50,00) e não vê Carlos
        self.client.force_login(self.prof_a1)
        comm_resp = self.client.get(reverse('finance:commission_list'))
        self.assertEqual(comm_resp.status_code, 200)
        self.assertContains(comm_resp, 'Ana Especialista')
        self.assertNotContains(comm_resp, 'Carlos Especialista')

        # Profissional recebe 403 ao tentar acessar o painel do Caixa Diário ou dar baixa em comissões
        self.assertEqual(
            self.client.get(reverse('finance:cash_dashboard')).status_code,
            403,
        )
        comm_ana = CommissionEntry.objects.get(order=order, professional=self.prof_a1)
        self.assertEqual(
            self.client.post(
                reverse('finance:commission_payout'),
                data={'entry_ids': [comm_ana.pk]},
            ).status_code,
            403,
        )

        # Gestor realiza a baixa de repasse da comissão de Ana e fecha o caixa diário
        self.client.force_login(self.gestor_a)
        payout_resp = self.client.post(
            reverse('finance:commission_payout'),
            data={'entry_ids': [comm_ana.pk]},
        )
        self.assertEqual(payout_resp.status_code, 302)
        comm_ana.refresh_from_db()
        self.assertEqual(comm_ana.status, CommissionStatusChoices.PAID)
        self.assertEqual(comm_ana.paid_by, self.gestor_a)

        # Lançamento manual de despesa no caixa (R$ 30.00) -> saldo esperado 200 - 30 = 170.00
        CashRegisterService.record_manual_transaction(
            salon=self.salon_a,
            transaction_type=CashTransactionTypeChoices.MANUAL_EXPENSE,
            amount=Decimal('30.00'),
            description='Compra de café e descartáveis',
            actor=self.gestor_a,
        )
        closed_session = CashRegisterService.close_session(
            salon=self.salon_a,
            closed_by=self.gestor_a,
            closing_balance_counted=Decimal('170.00'),
            notes='Fechamento sem divergências',
        )
        self.assertEqual(closed_session.status, CashRegisterStatusChoices.CLOSED)
        self.assertEqual(closed_session.closing_balance_expected, Decimal('170.00'))

        # SEC-B: Gestor do Salão A recebe 404 ao tentar pagar ou estornar comanda do Salão B
        order_b = ServiceOrder.objects.create(salon=self.salon_b)
        self.assertEqual(
            self.client.post(
                reverse('finance:order_checkout', args=[order_b.pk]),
                data={'payment_method_1': 'pix', 'amount_1': '50.00'},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse('finance:order_reverse', args=[order_b.pk]),
                data={'reason': 'Cross-tenant'},
            ).status_code,
            404,
        )
