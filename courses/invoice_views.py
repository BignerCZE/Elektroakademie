from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .invoices import invoice_pdf, render_invoice_html
from .models import Invoice, Order


def can_view_invoice(request, order_id):
    return order_id in request.session.get("invoice_order_ids", []) or (
        request.user.is_active and request.user.is_staff
        and request.user.has_perm("courses.view_invoice")
    )


@never_cache
@require_GET
def invoice_preview(request, order_id):
    if not can_view_invoice(request, order_id):
        raise Http404
    order = get_object_or_404(Order, pk=order_id)
    invoice = Invoice.objects.filter(order=order).first()
    response = HttpResponse(render_invoice_html(invoice, order=order))
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@never_cache
@require_GET
def invoice_download(request, order_id):
    if not can_view_invoice(request, order_id):
        raise Http404
    invoice = get_object_or_404(Invoice, order_id=order_id)
    try:
        content = invoice_pdf(invoice)
    except Exception:
        return HttpResponse("PDF se nyní nepodařilo vytvořit. Zkuste stažení znovu.", status=503)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="faktura-{invoice.number}.pdf"'
    return response
