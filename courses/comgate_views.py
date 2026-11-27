import json
import logging

from django.conf import settings
from django.db import DatabaseError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .comgate import (
    ComgateError, create_payment, credentials, fulfill_payment, matches_payment_mode, payment_status,
)
from .emails.transport import test_smtp_enabled
from .models import ComgatePayment, Order

logger = logging.getLogger(__name__)


def checkout_available():
    if not settings.COMGATE_CHECKOUT:
        return False
    if settings.COMGATE_TEST:
        return not settings.COMGATE_LIVE and (
            settings.EMAIL_TRANSPORT == "preview"
            or (settings.EMAIL_TRANSPORT == "smtp_test" and test_smtp_enabled())
        )
    return (
        settings.COMGATE_LIVE and not settings.DEBUG
        and settings.EMAIL_TRANSPORT == "smtp"
        and settings.SITE_URL.startswith("https://")
    )


def start_checkout(order):
    result_url = reverse("comgate_result", args=[order.pk])
    if not checkout_available():
        return redirect(result_url)

    payment, created = ComgatePayment.objects.get_or_create(order=order, defaults={"is_test": settings.COMGATE_TEST})
    if created:
        # A lost create response may still have created a remote transaction.
        # Keep the reservation and allow reconciliation through Comgate logs.
        try:
            transaction_id, redirect_url = create_payment(order, settings.SITE_URL + result_url, is_test=payment.is_test)
            payment.transaction_id = transaction_id
            payment.redirect_url = redirect_url
            payment.status = ComgatePayment.Status.PENDING
            payment.save(update_fields=["transaction_id", "redirect_url", "status"])
        except (ComgateError, DatabaseError) as exc:
            payment.status = ComgatePayment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.warning("Comgate create: objednávka %s, %s", order.pk, type(exc).__name__)

    if payment.is_test == settings.COMGATE_TEST and payment.status == ComgatePayment.Status.PENDING and payment.redirect_url:
        return redirect(payment.redirect_url)
    return redirect(result_url)


@never_cache
@require_GET
def checkout_result(request, order_id):
    if order_id not in request.session.get("invoice_order_ids", []):
        raise Http404
    order = get_object_or_404(Order, pk=order_id, course_type="4")
    payment = ComgatePayment.objects.filter(order=order).first()
    return render(request, "registration/comgate_result.html", {
        "order": order,
        "payment": payment,
        "invoice_ready": hasattr(order, "invoice"),
    })


@csrf_exempt
@require_POST
def webhook(request):
    if not settings.COMGATE_CHECKOUT:
        raise Http404
    if not checkout_available():
        return HttpResponse(status=503)
    if request.content_type != "application/json":
        return HttpResponse(status=415)
    try:
        payload = json.loads(request.body)
    except (ValueError, UnicodeError):
        return HttpResponse(status=400)
    if not isinstance(payload, dict):
        return HttpResponse(status=400)

    try:
        merchant, secret = credentials()
    except ComgateError:
        return HttpResponse(status=503)
    if (
        payload.get("merchant") != merchant
        or not isinstance(payload.get("secret"), str)
        or not constant_time_compare(payload["secret"], secret)
        or not matches_payment_mode(payload.get("test"), settings.COMGATE_TEST)
    ):
        return HttpResponse(status=403)
    transaction_id = payload.get("transId")
    if not isinstance(transaction_id, str) or not transaction_id or len(transaction_id) > 64:
        return HttpResponse(status=400)

    payment = ComgatePayment.objects.select_related("order").filter(
        transaction_id=transaction_id, order__course_type="4",
    ).first()
    if payment is None:
        return HttpResponse(status=404)
    if payment.is_test != settings.COMGATE_TEST:
        return HttpResponse(status=403)

    try:
        state = payment_status(payment.order, transaction_id, is_test=payment.is_test)
        if state == ComgatePayment.Status.PENDING:
            # Ask Comgate to retry if the final notification arrived before the status API caught up.
            return HttpResponse(status=503)
        if state == ComgatePayment.Status.PAID:
            fulfill_payment(payment)
        else:
            ComgatePayment.objects.filter(pk=payment.pk, status=ComgatePayment.Status.PENDING).update(status=state)
    except (ComgateError, DatabaseError) as exc:
        logger.warning("Comgate webhook: objednávka %s, %s", payment.order_id, type(exc).__name__)
        return HttpResponse(status=503)

    return HttpResponse(status=200)
