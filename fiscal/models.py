from django.core.exceptions import ValidationError
from django.db import models
from base.models import TenantScopedModel


class FiscalDocumentScopeChoices(models.TextChoices):
    NFSE_SERVICE = 'nfse_servico', 'NFS-e (Serviços Municipais)'
    NFCE_PRODUCT = 'nfce_produto', 'NFC-e (Venda de Produtos)'
    MIXED = 'misto', 'Misto (NFS-e Serviços + NFC-e Produtos)'


class FiscalDocumentStatusChoices(models.TextChoices):
    NOT_REQUESTED = 'nao_solicitada', 'Não solicitada'
    PENDING_FUTURE_INTEGRATION = (
        'pendente_integracao_futura',
        'Pendente de integração futura',
    )
    READY_TO_SEND = 'pronta_para_envio', 'Pronta para envio'
    ISSUED = 'emitida', 'Emitida'
    ISSUANCE_ERROR = 'erro_emissao', 'Erro na emissão'
    CANCELLED = 'cancelada', 'Cancelada / Estornada'


class FiscalDocumentRecord(TenantScopedModel):
    order = models.OneToOneField(
        'orders.ServiceOrder',
        on_delete=models.PROTECT,
        related_name='fiscal_record',
        verbose_name='Comanda',
    )
    document_scope = models.CharField(
        'Escopo fiscal',
        max_length=20,
        choices=FiscalDocumentScopeChoices.choices,
        default=FiscalDocumentScopeChoices.NFSE_SERVICE,
    )
    status = models.CharField(
        'Status fiscal',
        max_length=30,
        choices=FiscalDocumentStatusChoices.choices,
        default=FiscalDocumentStatusChoices.PENDING_FUTURE_INTEGRATION,
    )
    issuer_snapshot = models.JSONField(
        'Snapshot do emitente (Salão)',
        default=dict,
    )
    customer_snapshot = models.JSONField(
        'Snapshot do tomador (Cliente)',
        default=dict,
    )
    services_fiscal_payload = models.JSONField(
        'Payload fiscal de serviços (NFS-e / Salão-Parceiro)',
        default=list,
    )
    products_fiscal_payload = models.JSONField(
        'Payload fiscal de produtos (NFC-e)',
        default=list,
    )
    external_provider_name = models.CharField(
        'Provedor fiscal externo',
        max_length=80,
        blank=True,
        default='stub_noop_mvp',
    )
    external_reference_id = models.CharField(
        'Referência externa',
        max_length=120,
        blank=True,
    )
    fiscal_number = models.CharField('Número da nota', max_length=40, blank=True)
    fiscal_series = models.CharField('Série', max_length=10, blank=True)
    access_key = models.CharField(
        'Chave de acesso (44 dígitos)',
        max_length=60,
        blank=True,
    )
    xml_url = models.URLField('URL do XML', blank=True)
    pdf_danfe_url = models.URLField('URL do DANFE / DANFSE (PDF)', blank=True)
    last_error_message = models.TextField('Última mensagem de erro', blank=True)
    attempt_logs = models.JSONField(
        'Histórico de tentativas',
        default=list,
        blank=True,
    )

    class Meta:
        verbose_name = 'Registro de documento fiscal'
        verbose_name_plural = 'Registros de documentos fiscais'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return (
            f'Registro Fiscal — Comanda #{self.order_id} '
            f'({self.get_document_scope_display()} — {self.get_status_display()})'
        )

    def clean(self):
        super().clean()
        if self.salon_id and self.order_id and self.order.salon_id != self.salon_id:
            raise ValidationError({'order': 'A comanda vinculada pertence a outro salão.'})
