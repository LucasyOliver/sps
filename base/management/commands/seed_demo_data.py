from datetime import datetime, time, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from accounts.models import UserRoleChoices
from catalog.models import ProfessionalServiceCommission, Service, ServiceCategory
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
from orders.models import ServiceOrderStatusChoices
from orders.services import OrderService
from salons.models import Salon, SalonBusinessHours, TaxRegimeChoices, WeekdayChoices
from scheduling.models import (
    Appointment,
    AppointmentStatusChoices,
    ProfessionalSchedule,
)
from scheduling.services import SchedulingService

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Popula dados de demonstração multi-tenant (salões, equipe, serviços, regras de comissão, '
        'clientes, agendamentos passados/atuais/futuros, comandas pagas, estoque e registros fiscais).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow-non-debug',
            action='store_true',
            default=False,
            help='Permite executar em ambiente com DEBUG=False apenas quando explicitamente autorizado.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options.get('allow_non_debug'):
            raise CommandError(
                'Operação bloqueada por segurança (RNF-006): seed_demo_data não pode ser '
                'executado quando DEBUG=False sem a flag explícita --allow-non-debug.'
            )

        with transaction.atomic():
            summary = self._seed_all()

        self.stdout.write(
            self.style.SUCCESS(
                f'Carga demo concluída com sucesso: {summary["salons"]} salões, '
                f'{summary["users"]} usuários, {summary["services"]} serviços, '
                f'{summary["clients"]} clientes, {summary["appointments"]} agendamentos, '
                f'{summary["orders"]} comandas e {summary["products"]} produtos.'
            )
        )

    def _seed_all(self) -> dict:
        # 1. Superadmin SaaS Global
        superadmin, created = User.objects.get_or_create(
            email='superadmin@sps.local',
            defaults={
                'full_name': 'Superadmin Plataforma SPS',
                'role': UserRoleChoices.SUPERADMIN_SAAS,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            superadmin.set_password('SpsDemo@2026!')
            superadmin.save()

        # 2. Salão 1: Salão Alpha Studio & Barbearia
        salon_alpha, _ = Salon.objects.update_or_create(
            slug='salao-alpha',
            defaults={
                'name': 'Salão Alpha Beleza e Barbearia LTDA',
                'trade_name': 'Salão Alpha Studio',
                'phone': '11988880001',
                'email': 'contato@salaoalpha.com.br',
                'cancellation_min_hours': 3,
                'cnpj': '12345678000199',
                'municipal_registration': '11223344',
                'tax_regime': TaxRegimeChoices.SIMPLES_NACIONAL,
                'is_partner_salon_regime': True,
                'ibge_city_code': '3550308',
                'address_street': 'Av. Paulista',
                'address_number': '1000',
                'address_neighborhood': 'Bela Vista',
                'address_city': 'São Paulo',
                'address_state': 'SP',
                'address_zip_code': '01310100',
                'is_active': True,
            },
        )

        # 3. Salão 2: Salão Belle Femme & Spa
        salon_belle, _ = Salon.objects.update_or_create(
            slug='salao-belle',
            defaults={
                'name': 'Belle Femme Estética e Cabelo LTDA',
                'trade_name': 'Salão Belle Femme',
                'phone': '11988880002',
                'email': 'contato@bellefemme.com.br',
                'cancellation_min_hours': 2,
                'cnpj': '98765432000188',
                'municipal_registration': '55667788',
                'tax_regime': TaxRegimeChoices.MEI,
                'is_partner_salon_regime': False,
                'ibge_city_code': '3550308',
                'address_city': 'São Paulo',
                'address_state': 'SP',
                'is_active': True,
            },
        )

        self._seed_salon_ecosystem(salon_alpha, prefix='alpha')
        self._seed_salon_ecosystem(salon_belle, prefix='belle')

        return {
            'salons': Salon.objects.count(),
            'users': User.objects.count(),
            'services': Service.objects.count(),
            'clients': Client.objects.count(),
            'appointments': Appointment.objects.count(),
            'orders': salon_alpha.orders_serviceorder_set.count()
            + salon_belle.orders_serviceorder_set.count(),
            'products': Product.objects.count(),
        }

    def _seed_salon_ecosystem(self, salon: Salon, *, prefix: str):
        # Expediente semanal (Segunda a Sábado das 09:00 às 19:00; Domingo fechado)
        for weekday in WeekdayChoices.values:
            is_open = weekday != WeekdayChoices.SUNDAY
            SalonBusinessHours.objects.update_or_create(
                salon=salon,
                weekday=weekday,
                defaults={
                    'is_open': is_open,
                    'opening_time': time(9, 0) if is_open else None,
                    'closing_time': time(19, 0) if is_open else None,
                },
            )

        gestor = self._upsert_user(
            email=f'gestor@{prefix}.sps.local',
            full_name=f'Gestor {salon.trade_name}',
            role=UserRoleChoices.GESTOR,
            salon=salon,
        )
        recep = self._upsert_user(
            email=f'recepcao@{prefix}.sps.local',
            full_name=f'Recepção {salon.trade_name}',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=salon,
        )
        prof_1 = self._upsert_user(
            email=f'ana@{prefix}.sps.local',
            full_name=f'Ana Especialista ({prefix.upper()})',
            role=UserRoleChoices.PROFISSIONAL,
            salon=salon,
            tax_document='11122233344',
        )
        prof_2 = self._upsert_user(
            email=f'carlos@{prefix}.sps.local',
            full_name=f'Carlos Especialista ({prefix.upper()})',
            role=UserRoleChoices.PROFISSIONAL,
            salon=salon,
            tax_document='55566677788',
        )

        for prof in (prof_1, prof_2):
            for weekday in range(0, 6):
                ProfessionalSchedule.objects.update_or_create(
                    salon=salon,
                    professional=prof,
                    weekday=weekday,
                    defaults={
                        'is_working': True,
                        'start_time': time(9, 0),
                        'end_time': time(18, 0),
                        'break_start_time': time(12, 0),
                        'break_end_time': time(13, 0),
                    },
                )

        cat_cabelo, _ = ServiceCategory.objects.update_or_create(
            salon=salon,
            name='Cabelo e Barbearia',
            defaults={'description': 'Cortes, escovas e barbearia clássica'},
        )
        cat_trat, _ = ServiceCategory.objects.update_or_create(
            salon=salon,
            name='Tratamentos Capilares',
            defaults={'description': 'Hidratação, reconstrução e nutrição'},
        )

        srv_corte, _ = Service.objects.update_or_create(
            salon=salon,
            name='Corte + Finalização',
            defaults={
                'category': cat_cabelo,
                'duration_minutes': 45,
                'base_price': Decimal('90.00'),
                'default_commission_pct': Decimal('40.00'),
                'lc116_service_code': '06.01',
                'cnae_code': '9602-5/01',
                'iss_rate_pct': Decimal('2.00'),
                'is_active': True,
            },
        )
        srv_corte.professionals.set([prof_1, prof_2])

        srv_hidratacao, _ = Service.objects.update_or_create(
            salon=salon,
            name='Hidratação Profunda',
            defaults={
                'category': cat_trat,
                'duration_minutes': 60,
                'base_price': Decimal('130.00'),
                'default_commission_pct': Decimal('45.00'),
                'lc116_service_code': '06.01',
                'cnae_code': '9602-5/01',
                'iss_rate_pct': Decimal('2.00'),
                'is_active': True,
            },
        )
        srv_hidratacao.professionals.set([prof_1, prof_2])

        ProfessionalServiceCommission.objects.update_or_create(
            salon=salon,
            professional=prof_1,
            service=srv_corte,
            defaults={'commission_pct': Decimal('50.00'), 'is_active': True},
        )

        # Produtos e movimentações de estoque (1 com saldo saudável e 1 em estoque crítico)
        prod_pomada, created_p1 = Product.objects.update_or_create(
            salon=salon,
            name='Pomada Modeladora Matte 120g',
            defaults={
                'sku': f'POM-{prefix.upper()}-01',
                'usage_type': ProductUsageTypeChoices.BOTH,
                'unit': ProductUnitChoices.UNIT,
                'cost_price': Decimal('22.00'),
                'sale_price': Decimal('48.00'),
                'min_stock_alert': 2,
                'ncm_code': '33059000',
                'cest_code': '2002000',
                'cfop_default': '5102',
                'is_active': True,
            },
        )
        if created_p1 or prod_pomada.current_stock == 0:
            StockService.register_movement(
                salon=salon,
                product=prod_pomada,
                movement_type=StockMovementTypeChoices.PURCHASE_IN,
                quantity=10,
                actor=gestor,
                reason='Carga inicial de demonstração',
            )

        prod_critico, created_p2 = Product.objects.update_or_create(
            salon=salon,
            name='Óleo Reparador Argan 30ml',
            defaults={
                'sku': f'OLE-{prefix.upper()}-02',
                'usage_type': ProductUsageTypeChoices.SALE,
                'unit': ProductUnitChoices.UNIT,
                'cost_price': Decimal('18.00'),
                'sale_price': Decimal('42.00'),
                'min_stock_alert': 5,
                'ncm_code': '33059000',
                'cfop_default': '5102',
                'is_active': True,
            },
        )
        if created_p2 and prod_critico.current_stock == 0:
            StockService.register_movement(
                salon=salon,
                product=prod_critico,
                movement_type=StockMovementTypeChoices.PURCHASE_IN,
                quantity=2,
                actor=gestor,
                reason='Estoque inicial em nível de alerta para demo',
            )

        # Clientes (1 ativo recente e 1 inativo há > 60 dias)
        client_active, _ = Client.objects.update_or_create(
            salon=salon,
            phone='11977771001',
            defaults={
                'full_name': f'Mariana Cliente ({prefix.upper()})',
                'email': f'mariana.{prefix}@cliente.local',
                'cpf_cnpj': '12345678901',
                'address_city': 'São Paulo',
                'address_state': 'SP',
                'ibge_city_code': '3550308',
            },
        )
        Client.objects.update_or_create(
            salon=salon,
            phone='11977771002',
            defaults={
                'full_name': f'Roberto Cliente Inativo ({prefix.upper()})',
                'email': f'roberto.{prefix}@cliente.local',
            },
        )

        # Agendamentos (passado concluído e futuro confirmado)
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        future_start = timezone.make_aware(datetime.combine(next_monday, time(10, 0)), tz)

        if not Appointment.objects.for_salon(salon).filter(start_at=future_start).exists():
            SchedulingService.create_appointment(
                salon=salon,
                client=client_active,
                professional=prof_1,
                start_at=future_start,
                services=[srv_corte, srv_hidratacao],
                notes='Agendamento futuro de demonstração',
                created_by=recep,
            )

        # Caixa aberto + Comanda paga gerando comissão e FiscalDocumentRecord
        if CashRegisterService.get_open_session(salon) is None:
            CashRegisterService.open_session(
                salon=salon,
                opened_by=gestor,
                opening_balance=Decimal('150.00'),
                notes='Sessão de caixa de demonstração',
            )

        if not salon.orders_serviceorder_set.filter(
            status=ServiceOrderStatusChoices.CLOSED_PAID
        ).exists():
            order = OrderService.open_order(
                salon=salon,
                client=client_active,
                opened_by=recep,
                notes='Comanda demo paga com serviço + produto',
            )
            OrderService.add_service_item(
                order=order,
                service=srv_corte,
                professional=prof_1,
            )
            OrderService.add_product_item(
                order=order,
                product=prod_pomada,
                quantity=1,
            )
            order.refresh_from_db()
            OrderCheckoutService.close_and_pay_order(
                salon=salon,
                order=order,
                payments=[
                    {
                        'payment_method': PaymentMethodChoices.PIX,
                        'amount': order.total_amount,
                    }
                ],
                actor=recep,
            )

    @staticmethod
    def _upsert_user(*, email: str, full_name: str, role: str, salon: Salon, tax_document: str = ''):
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'role': role,
                'salon': salon,
                'tax_document': tax_document,
                'is_active': True,
            },
        )
        if created:
            user.set_password('SpsDemo@2026!')
            user.save()
        return user
