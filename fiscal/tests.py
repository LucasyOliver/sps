from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from accounts.models import UserRoleChoices
from catalog.models import Service
from fiscal.models import FiscalDocumentScopeChoices, FiscalDocumentStatusChoices
from fiscal.services import StubFiscalGatewayAdapter
from inventory.models import (
    Product,
    ProductUnitChoices,
    ProductUsageTypeChoices,
    StockMovementTypeChoices,
)
from inventory.services import StockService
from orders.services import OrderService
from salons.models import Salon, TaxRegimeChoices

User = get_user_model()


class FiscalPreparationAdapterTests(TestCase):
    def setUp(self):
        self.salon = Salon.objects.create(
            name='Salão Fiscal Teste LTDA',
            trade_name='Salão Fiscal',
            slug='salao-fiscal',
            cnpj='98765432000188',
            tax_regime=TaxRegimeChoices.MEI,
            is_partner_salon_regime=False,
        )
        self.gestor = User.objects.create_user(
            email='gestor@fiscal.com.br',
            password='StrongPassword123!',
            full_name='Gestor Fiscal',
            role=UserRoleChoices.GESTOR,
            salon=self.salon,
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name='Barba Express',
            duration_minutes=30,
            base_price=Decimal('60.00'),
            default_commission_pct=Decimal('40.00'),
            lc116_service_code='06.01',
        )
        self.product = Product.objects.create(
            salon=self.salon,
            name='Shampoo Anticaspa',
            sku='SH-01',
            usage_type=ProductUsageTypeChoices.SALE,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('15.00'),
            sale_price=Decimal('35.00'),
            ncm_code='33051000',
            cfop_default='5102',
        )
        StockService.register_movement(
            salon=self.salon,
            product=self.product,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=3,
            actor=self.gestor,
        )

    def test_stub_fiscal_adapter_determines_nfse_and_nfce_scopes(self):
        """S07-T02 / RF-013: Verifica escopo nfse_servico vs nfce_produto e log de tentativa stub."""
        adapter = StubFiscalGatewayAdapter()

        # 1. Comanda exclusiva de serviços -> nfse_servico
        order_srv = OrderService.open_order(salon=self.salon, opened_by=self.gestor)
        OrderService.add_service_item(
            order=order_srv,
            service=self.service,
            professional=self.gestor,
        )
        rec_srv = adapter.prepare_from_order(order_srv)
        self.assertEqual(rec_srv.document_scope, FiscalDocumentScopeChoices.NFSE_SERVICE)
        self.assertEqual(
            rec_srv.status,
            FiscalDocumentStatusChoices.PENDING_FUTURE_INTEGRATION,
        )
        self.assertEqual(rec_srv.customer_snapshot['identified'], False)
        self.assertEqual(len(rec_srv.attempt_logs), 1)

        # 2. Comanda exclusiva de produtos -> nfce_produto
        order_prod = OrderService.open_order(salon=self.salon, opened_by=self.gestor)
        OrderService.add_product_item(
            order=order_prod,
            product=self.product,
            quantity=1,
        )
        rec_prod = adapter.prepare_from_order(order_prod)
        self.assertEqual(rec_prod.document_scope, FiscalDocumentScopeChoices.NFCE_PRODUCT)
        self.assertEqual(rec_prod.products_fiscal_payload[0]['ncm_code'], '33051000')
