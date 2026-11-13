from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import UserRoleChoices
from inventory.forms import StockMovementForm
from inventory.models import (
    Product,
    ProductUnitChoices,
    ProductUsageTypeChoices,
    StockMovement,
    StockMovementTypeChoices,
)
from inventory.services import InsufficientStockError, StockService
from salons.models import Salon

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class InventoryModelServiceAndIsolationTests(TestCase):
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
        self.prof_a = User.objects.create_user(
            email='prof@alpha.com.br',
            password='StrongPassword123!',
            full_name='Profissional Alpha',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )

        self.product_sale_a = Product.objects.create(
            salon=self.salon_a,
            name='Pomada Modeladora Matte 120g',
            sku='POM-001',
            usage_type=ProductUsageTypeChoices.BOTH,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('22.00'),
            sale_price=Decimal('45.00'),
            min_stock_alert=2,
            ncm_code='33059000',
            cest_code='2002000',
            cfop_default='5102',
        )
        self.product_sale_only_a = Product.objects.create(
            salon=self.salon_a,
            name='Óleo para Barba 30ml',
            sku='OLE-002',
            usage_type=ProductUsageTypeChoices.SALE,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('18.00'),
            sale_price=Decimal('39.90'),
            min_stock_alert=3,
        )
        self.product_b = Product.objects.create(
            salon=self.salon_b,
            name='Pomada Modeladora Matte 120g',
            sku='POM-001',
            usage_type=ProductUsageTypeChoices.SALE,
            unit=ProductUnitChoices.UNIT,
            cost_price=Decimal('20.00'),
            sale_price=Decimal('40.00'),
            min_stock_alert=1,
        )

    def test_product_fiscal_metadata_validation_and_uniqueness_per_salon(self):
        """S06-T01 / RF-008: Valida códigos fiscais (NCM, CEST, CFOP) e unicidade por salão."""
        invalid_product = Product(
            salon=self.salon_a,
            name='Shampoo Inválido',
            ncm_code='123',
            cest_code='99',
            cfop_default='51',
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_product.full_clean()
        self.assertIn('ncm_code', ctx.exception.message_dict)
        self.assertIn('cest_code', ctx.exception.message_dict)
        self.assertIn('cfop_default', ctx.exception.message_dict)

        # NCM/CEST/CFOP com pontuação são normalizados para dígitos
        valid_product = Product(
            salon=self.salon_a,
            name='Shampoo Neutro 1L',
            usage_type=ProductUsageTypeChoices.INTERNAL,
            ncm_code='3305.10.00',
            cest_code='20.017.00',
            cfop_default='5.102',
        )
        valid_product.full_clean()
        self.assertEqual(valid_product.ncm_code, '33051000')
        self.assertEqual(valid_product.cest_code, '2001700')
        self.assertEqual(valid_product.cfop_default, '5102')

    def test_stock_movements_negative_balance_block_low_stock_alert_and_immutability(self):
        """
        S06-T02 / RF-008: Movimentações atualizam saldo de forma atômica, bloqueiam saldo
        negativo, sinalizam estoque mínimo e impedem edição/exclusão do livro razão.
        """
        # Entrada de compra de 5 unidades -> saldo = 5 (acima do mínimo de 2)
        mov_in = StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=5,
            actor=self.gestor_a,
            reason='Nota de compra #101',
        )
        self.assertEqual(mov_in.quantity_delta, 5)
        self.assertEqual(mov_in.balance_after, 5)
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 5)
        self.assertFalse(self.product_sale_a.is_below_min_stock)

        # Consumo interno de 3 unidades -> saldo = 2 (atinge min_stock_alert = 2 -> alerta ativo)
        mov_internal = StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.INTERNAL_OUT,
            quantity=3,
            actor=self.gestor_a,
            reason='Uso na bancada',
        )
        self.assertEqual(mov_internal.quantity_delta, -3)
        self.assertEqual(mov_internal.balance_after, 2)
        self.product_sale_a.refresh_from_db()
        self.assertTrue(self.product_sale_a.is_below_min_stock)
        self.assertIn(
            self.product_sale_a,
            list(StockService.low_stock_products(self.salon_a)),
        )

        # Tentativa de retirar 3 unidades quando o saldo é 2 -> bloqueada (InsufficientStockError)
        with self.assertRaises(InsufficientStockError):
            StockService.register_movement(
                salon=self.salon_a,
                product=self.product_sale_a,
                movement_type=StockMovementTypeChoices.INTERNAL_OUT,
                quantity=3,
                actor=self.gestor_a,
            )
        self.product_sale_a.refresh_from_db()
        self.assertEqual(self.product_sale_a.current_stock, 2)

        # Produto exclusivo de venda não pode sofrer baixa por consumo interno
        StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_only_a,
            movement_type=StockMovementTypeChoices.PURCHASE_IN,
            quantity=4,
            actor=self.gestor_a,
        )
        with self.assertRaises(ValidationError):
            StockService.register_movement(
                salon=self.salon_a,
                product=self.product_sale_only_a,
                movement_type=StockMovementTypeChoices.INTERNAL_OUT,
                quantity=1,
                actor=self.gestor_a,
            )

        # Ajuste de inventário sem motivo deve falhar; com motivo deve funcionar
        with self.assertRaises(ValidationError):
            StockService.register_movement(
                salon=self.salon_a,
                product=self.product_sale_a,
                movement_type=StockMovementTypeChoices.ADJUSTMENT,
                quantity=-1,
                actor=self.gestor_a,
                reason='',
            )
        mov_adj = StockService.register_movement(
            salon=self.salon_a,
            product=self.product_sale_a,
            movement_type=StockMovementTypeChoices.ADJUSTMENT,
            quantity=-1,
            actor=self.gestor_a,
            reason='Avaria de embalagem na prateleira',
        )
        self.assertEqual(mov_adj.balance_after, 1)

        # Livro razão imutável: não permite alterar nem excluir StockMovement existente
        with self.assertRaises(ValidationError):
            mov_adj.reason = 'Tentativa de adulterar histórico'
            mov_adj.save()
        with self.assertRaises(ValidationError):
            mov_adj.delete()

    def test_inventory_views_permissions_and_cross_tenant_isolation(self):
        """SEC-A, SEC-B, SEC-C, SEC-D: Permissões de estoque por perfil e isolamento entre salões."""
        # Gestor cadastra produto já com saldo inicial de 8 unidades
        self.client.force_login(self.gestor_a)
        create_resp = self.client.post(
            reverse('inventory:product_create'),
            data={
                'name': 'Cera Modeladora Efeito Teia',
                'sku': 'CER-010',
                'usage_type': ProductUsageTypeChoices.SALE,
                'unit': ProductUnitChoices.UNIT,
                'cost_price': '19.50',
                'sale_price': '42.00',
                'min_stock_alert': '3',
                'initial_stock': '8',
                'tax_origin': '0',
                'is_active': 'on',
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        wax = Product.objects.for_salon(self.salon_a).get(sku='CER-010')
        self.assertEqual(wax.current_stock, 8)
        self.assertEqual(wax.movements.count(), 1)

        # SEC-B: Gestor do Salão A recebe 404 ao tentar editar produto do Salão B
        self.assertEqual(
            self.client.get(
                reverse('inventory:product_edit', args=[self.product_b.pk])
            ).status_code,
            404,
        )

        # SEC-D: StockMovementForm rejeita produto de outro salão
        cross_form = StockMovementForm(
            data={
                'product': self.product_b.pk,
                'movement_type': StockMovementTypeChoices.PURCHASE_IN,
                'quantity': 5,
            },
            salon=self.salon_a,
        )
        self.assertFalse(cross_form.is_valid())
        self.assertIn('product', cross_form.errors)

        # SEC-C: Recepcionista consulta estoque (200), mas recebe 403 ao criar produto ou movimentar
        self.client.force_login(self.recep_a)
        self.assertEqual(
            self.client.get(reverse('inventory:product_list')).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('inventory:product_create')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('inventory:movement_create')).status_code,
            403,
        )

        # SEC-C: Profissional recebe 403 ao tentar acessar qualquer tela de estoque
        self.client.force_login(self.prof_a)
        self.assertEqual(
            self.client.get(reverse('inventory:product_list')).status_code,
            403,
        )
