from decimal import Decimal
from django.utils import timezone
from catalog.services import calculate_commission_amount
from fiscal.models import (
    FiscalDocumentRecord,
    FiscalDocumentScopeChoices,
    FiscalDocumentStatusChoices,
)
from salons.models import normalize_digits


class FiscalGatewayAdapter:
    """
    Contrato base desacoplado para preparação e futura emissão de NFS-e (serviços)
    e NFC-e (produtos) (RF-013, DEC-003).
    """

    def prepare_from_order(self, order) -> FiscalDocumentRecord:
        """Consolida snapshots fiscais de emitente (Salon), tomador (Client), serviços e produtos."""
        raise NotImplementedError

    def request_issuance(self, fiscal_record: FiscalDocumentRecord) -> dict:
        """Dispara ou simula a transmissão assíncrona para provedor externo."""
        raise NotImplementedError

    def cancel_from_order_reversal(self, order, reason: str) -> FiscalDocumentRecord | None:
        """Marca o registro fiscal como cancelado quando a comanda paga é estornada."""
        raise NotImplementedError


class StubFiscalGatewayAdapter(FiscalGatewayAdapter):
    """
    Implementação NoOp/Stub oficial do MVP (DEC-003, RF-013).
    Popula integralmente o FiscalDocumentRecord no fechamento da comanda sem chamada
    bloqueante externa, deixando o payload pronto para futura task Celery de integração.
    """

    provider_name = 'stub_noop_mvp'

    @staticmethod
    def _build_issuer_snapshot(salon) -> dict:
        return {
            'salon_id': salon.pk,
            'name': salon.name,
            'trade_name': salon.trade_name,
            'cnpj': normalize_digits(salon.cnpj),
            'municipal_registration': salon.municipal_registration,
            'state_registration': salon.state_registration,
            'tax_regime': salon.tax_regime,
            'is_partner_salon_regime': salon.is_partner_salon_regime,
            'ibge_city_code': normalize_digits(salon.ibge_city_code),
            'address': {
                'street': salon.address_street,
                'number': salon.address_number,
                'complement': salon.address_complement,
                'neighborhood': salon.address_neighborhood,
                'city': salon.address_city,
                'state': salon.address_state,
                'zip_code': normalize_digits(salon.address_zip_code),
            },
        }

    @staticmethod
    def _build_customer_snapshot(client) -> dict:
        if client is None:
            return {'identified': False}
        return {
            'identified': True,
            'client_id': client.pk,
            'full_name': client.full_name,
            'cpf_cnpj': normalize_digits(client.cpf_cnpj),
            'email': client.email,
            'phone': normalize_digits(client.phone),
            'ibge_city_code': normalize_digits(client.ibge_city_code),
            'address': {
                'street': client.address_street,
                'number': client.address_number,
                'complement': client.address_complement,
                'neighborhood': client.address_neighborhood,
                'city': client.address_city,
                'state': client.address_state,
                'zip_code': normalize_digits(client.address_zip_code),
            },
        }

    @staticmethod
    def _build_services_payload(salon, service_items) -> list[dict]:
        payload = []
        for item in service_items:
            srv = item.service
            prof = item.professional
            comm_pct = item.applied_commission_pct or Decimal('0.00')
            partner_share = calculate_commission_amount(item.net_price, comm_pct)
            salon_retained = item.net_price - partner_share
            payload.append(
                {
                    'order_service_item_id': item.pk,
                    'service_id': srv.pk,
                    'service_name': srv.name,
                    'lc116_service_code': srv.lc116_service_code,
                    'cnae_code': srv.cnae_code,
                    'iss_rate_pct': str(srv.iss_rate_pct) if srv.iss_rate_pct is not None else None,
                    'gross_price': str(item.gross_price),
                    'discount_amount': str(item.discount_amount),
                    'net_price': str(item.net_price),
                    'partner_salon_split': {
                        'enabled': bool(salon.is_partner_salon_regime),
                        'professional_id': prof.pk,
                        'professional_name': prof.full_name,
                        'professional_tax_document': prof.tax_document,
                        'commission_pct': str(comm_pct),
                        'partner_quota_amount': str(partner_share),
                        'salon_quota_amount': str(salon_retained),
                    },
                }
            )
        return payload

    @staticmethod
    def _build_products_payload(product_items) -> list[dict]:
        payload = []
        for item in product_items:
            prod = item.product
            payload.append(
                {
                    'order_product_item_id': item.pk,
                    'product_id': prod.pk,
                    'product_name': prod.name,
                    'sku': prod.sku,
                    'unit': prod.unit,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'total_price': str(item.total_price),
                    'ncm_code': prod.ncm_code,
                    'cest_code': prod.cest_code,
                    'cfop_default': prod.cfop_default,
                    'tax_origin': prod.tax_origin,
                    'icms_rate_pct': (
                        str(prod.icms_rate_pct) if prod.icms_rate_pct is not None else None
                    ),
                    'pis_cofins_regime': prod.pis_cofins_regime,
                }
            )
        return payload

    def prepare_from_order(self, order) -> FiscalDocumentRecord:
        salon = order.salon
        service_items = list(order.service_items.select_related('service', 'professional'))
        product_items = list(order.product_items.select_related('product'))

        has_services = bool(service_items)
        has_products = bool(product_items)
        if has_services and has_products:
            scope = FiscalDocumentScopeChoices.MIXED
        elif has_products:
            scope = FiscalDocumentScopeChoices.NFCE_PRODUCT
        else:
            scope = FiscalDocumentScopeChoices.NFSE_SERVICE

        issuer_snapshot = self._build_issuer_snapshot(salon)
        customer_snapshot = self._build_customer_snapshot(order.client)
        services_payload = self._build_services_payload(salon, service_items)
        products_payload = self._build_products_payload(product_items)

        record, _created = FiscalDocumentRecord.objects.update_or_create(
            salon=salon,
            order=order,
            defaults={
                'document_scope': scope,
                'status': FiscalDocumentStatusChoices.PENDING_FUTURE_INTEGRATION,
                'issuer_snapshot': issuer_snapshot,
                'customer_snapshot': customer_snapshot,
                'services_fiscal_payload': services_payload,
                'products_fiscal_payload': products_payload,
                'external_provider_name': self.provider_name,
            },
        )
        self.request_issuance(record)
        return record

    def request_issuance(self, fiscal_record: FiscalDocumentRecord) -> dict:
        logs = list(fiscal_record.attempt_logs or [])
        entry = {
            'timestamp': timezone.now().isoformat(),
            'provider': self.provider_name,
            'action': 'prepare_stub_noop',
            'status': FiscalDocumentStatusChoices.PENDING_FUTURE_INTEGRATION,
            'message': 'Payload fiscal consolidado localmente (MVP sem transmissão externa).',
        }
        logs.append(entry)
        fiscal_record.attempt_logs = logs
        fiscal_record.save(update_fields=['attempt_logs', 'updated_at'])
        return entry

    def cancel_from_order_reversal(self, order, reason: str) -> FiscalDocumentRecord | None:
        record = FiscalDocumentRecord.objects.for_salon(order.salon).filter(order=order).first()
        if record is None:
            return None
        logs = list(record.attempt_logs or [])
        logs.append(
            {
                'timestamp': timezone.now().isoformat(),
                'provider': self.provider_name,
                'action': 'order_reversal_cancel',
                'status': FiscalDocumentStatusChoices.CANCELLED,
                'reason': reason,
            }
        )
        record.status = FiscalDocumentStatusChoices.CANCELLED
        record.attempt_logs = logs
        record.save(update_fields=['status', 'attempt_logs', 'updated_at'])
        return record
