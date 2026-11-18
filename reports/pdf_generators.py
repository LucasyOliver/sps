from decimal import Decimal
import io
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _finalize_pdf_with_metadata(raw_pdf_bytes: bytes, *, title: str, salon_name: str) -> bytes:
    """
    Pós-processa o PDF gerado pelo ReportLab utilizando PyPDF para injetar metadados
    de auditoria institucional do salão (RF-011, RNF-005).
    """
    reader = PdfReader(io.BytesIO(raw_pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            '/Title': title,
            '/Author': f'SPS — {salon_name}',
            '/Creator': 'SPS (Sistema Para Salões)',
            '/Producer': 'ReportLab + PyPDF',
        }
    )
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def generate_commissions_pdf(*, salon, entries, professional=None) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    _width, height = A4
    y = height - 50

    title = f'Extrato de Comissões — {salon.trade_name}'
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(40, y, title)
    y -= 20

    pdf.setFont('Helvetica', 10)
    prof_label = professional.full_name if professional else 'Todos os Profissionais'
    pdf.drawString(
        40,
        y,
        f'Profissional: {prof_label} | Emitido em: {timezone.localtime():%d/%m/%Y %H:%M}',
    )
    y -= 25

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(40, y, 'Data')
    pdf.drawString(125, y, 'Profissional')
    pdf.drawString(250, y, 'Serviço (Comanda)')
    pdf.drawString(395, y, 'Base (R$)')
    pdf.drawString(455, y, '% / Comissão')
    pdf.drawString(525, y, 'Status')
    y -= 15
    pdf.setFont('Helvetica', 8)

    total_comm = Decimal('0.00')
    for entry in entries:
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 8)
        dt_str = timezone.localtime(entry.created_at).strftime('%d/%m/%Y %H:%M')
        srv_str = f'{entry.order_service_item.service.name[:20]} (#{entry.order_id})'
        pdf.drawString(40, y, dt_str)
        pdf.drawString(125, y, entry.professional.full_name[:22])
        pdf.drawString(250, y, srv_str)
        pdf.drawString(395, y, f'{entry.base_amount}')
        pdf.drawString(455, y, f'{entry.commission_pct}% / R$ {entry.commission_amount}')
        pdf.drawString(525, y, entry.get_status_display()[:12])
        total_comm += entry.commission_amount
        y -= 14

    y -= 10
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(40, y, f'Total de Comissões Listadas: R$ {total_comm}')
    pdf.save()

    return _finalize_pdf_with_metadata(
        buf.getvalue(),
        title=title,
        salon_name=salon.trade_name,
    )


def generate_cash_closing_pdf(*, salon, cash_session) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    _width, height = A4
    y = height - 50

    title = f'Relatório de Fechamento de Caixa #{cash_session.pk} — {salon.trade_name}'
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawString(40, y, title)
    y -= 20

    pdf.setFont('Helvetica', 10)
    pdf.drawString(
        40,
        y,
        f'Status: {cash_session.get_status_display()} | '
        f'Aberto por: {cash_session.opened_by.full_name} em '
        f'{timezone.localtime(cash_session.opened_at):%d/%m/%Y %H:%M}',
    )
    y -= 16
    pdf.drawString(
        40,
        y,
        f'Saldo Inicial: R$ {cash_session.opening_balance} | '
        f'Saldo Esperado: R$ {cash_session.closing_balance_expected} | '
        f'Saldo Conferido: R$ {cash_session.closing_balance_counted if cash_session.closing_balance_counted is not None else "—"}',
    )
    y -= 25

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(40, y, 'Data/Hora')
    pdf.drawString(130, y, 'Tipo')
    pdf.drawString(260, y, 'Meio')
    pdf.drawString(340, y, 'Descrição')
    pdf.drawString(500, y, 'Valor (R$)')
    y -= 15
    pdf.setFont('Helvetica', 8)

    for tx in cash_session.transactions.all():
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 8)
        dt_str = timezone.localtime(tx.created_at).strftime('%d/%m/%Y %H:%M')
        pdf.drawString(40, y, dt_str)
        pdf.drawString(130, y, tx.get_transaction_type_display()[:22])
        pdf.drawString(260, y, tx.get_payment_method_display()[:15])
        pdf.drawString(340, y, tx.description[:28])
        pdf.drawString(500, y, f'{tx.signed_amount}')
        y -= 14

    pdf.save()
    return _finalize_pdf_with_metadata(
        buf.getvalue(),
        title=title,
        salon_name=salon.trade_name,
    )


def generate_inventory_pdf(*, salon, products, movements) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    _width, height = A4
    y = height - 50

    title = f'Posição e Movimentação de Estoque — {salon.trade_name}'
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawString(40, y, title)
    y -= 22

    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(40, y, '1. Posição Atual de Produtos')
    y -= 16
    pdf.setFont('Helvetica', 8)

    for prod in products:
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 8)
        alert_tag = ' [ESTOQUE CRÍTICO]' if prod.is_below_min_stock else ''
        pdf.drawString(
            40,
            y,
            f'{prod.name} (SKU: {prod.sku or "—"}) — Saldo: {prod.current_stock} {prod.unit} '
            f'(Mín: {prod.min_stock_alert}) | Venda: R$ {prod.sale_price}{alert_tag}',
        )
        y -= 13

    y -= 12
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(40, y, '2. Últimas Movimentações Auditadas')
    y -= 16
    pdf.setFont('Helvetica', 8)

    for mov in movements[:40]:
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 8)
        dt_str = timezone.localtime(mov.created_at).strftime('%d/%m/%Y %H:%M')
        pdf.drawString(
            40,
            y,
            f'{dt_str} | {mov.product.name[:24]} | {mov.get_movement_type_display()} | '
            f'Delta: {mov.quantity_delta:+} | Saldo após: {mov.balance_after}',
        )
        y -= 13

    pdf.save()
    return _finalize_pdf_with_metadata(
        buf.getvalue(),
        title=title,
        salon_name=salon.trade_name,
    )
