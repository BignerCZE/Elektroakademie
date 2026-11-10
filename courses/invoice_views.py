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


@never_cache
@require_GET
def admin_invoice_pdf(request, order_id):
    # Admin access never falls back to the public checkout session grant.
    if not (request.user.is_active and request.user.is_staff
            and request.user.has_perm("courses.view_invoice")):
        raise Http404
    invoice = get_object_or_404(Invoice, order_id=order_id)
    if not invoice.pdf_content:
        return HttpResponse("U vystavené faktury není uložené PDF. Kontaktujte správce.", status=503)
    response = HttpResponse(bytes(invoice.pdf_content), content_type="application/pdf")
    disposition = "attachment" if request.GET.get("download") == "1" else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="faktura-{invoice.number}.pdf"'
    return response
