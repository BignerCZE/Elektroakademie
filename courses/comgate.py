import os
import re
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F

from .models import Order
from .workflows import process_order_payment

API_URL = "https://payments.comgate.cz/v2.0/payment"
TRANSACTION_ID = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")

STATES = {"PENDING", "PAID", "CANCELLED"}


class ComgateError(Exception):
    pass


def credentials():
    merchant = os.getenv("COMGATE_MERCHANT_ID", "").strip()
    secret = os.getenv("COMGATE_SECRET", "")
    if not merchant or not secret.strip():
        raise ComgateError("Doplňte COMGATE_MERCHANT_ID a COMGATE_SECRET do lokálního .env.")
    return merchant, secret


def order_reference(order):
    return f"EA4-{order.pk}-{order.created_at:%Y%m%d%H%M%S%f}"


def request_comgate(method, url, auth, expected_status, **kwargs):
    try:
        response = requests.request(
            method, url, auth=auth, timeout=(5, 20), allow_redirects=False, **kwargs
        )
    except requests.RequestException as exc:
        raise ComgateError(f"Spojení s Comgate selhalo ({type(exc).__name__}).") from None

    try:
        data = response.json()
    except ValueError:
        raise ComgateError(f"Comgate HTTP {response.status_code}: odpověď bez JSON.") from None

    if not isinstance(data, dict):
        raise ComgateError(f"Comgate HTTP {response.status_code}: neočekávaný formát JSON.")
    code = data.get("code")
    if response.status_code != expected_status or type(code) is not int or code != 0:
        code_label = str(code) if type(code) is int else "nedostupný"
        raise ComgateError(f"Comgate HTTP {response.status_code}, kód API {code_label}.")
    return data


def validate_transaction_id(transaction_id):
    if not isinstance(transaction_id, str) or not TRANSACTION_ID.fullmatch(transaction_id):
        raise ComgateError("Chybí platné ID transakce Comgate.")
    return transaction_id


def create_payment(order, return_url):
    auth = credentials()
    data = request_comgate(
        "POST", f"{API_URL}.json", auth, 201,
        json={
            "test": True,
            "price": order.total_price * 100,
            "curr": "CZK",
            "label": "Elektro §4",
            "refId": order_reference(order),
            "method": "ALL",
            "email": order.contact_email,
            "fullName": order.contact_full_name,
            "delivery": "ELECTRONIC_DELIVERY",
            "category": "OTHER",
            "lang": "cs",
            "url_paid": return_url,
            "url_cancelled": return_url,
            "url_pending": return_url,
        },
    )
    transaction_id = validate_transaction_id(data.get("transId"))
    redirect_url = data.get("redirect")
    if not isinstance(redirect_url, str) or not redirect_url:
        raise ComgateError(f"Comgate nevrátila adresu brány. Transakce: {transaction_id}.")
    try:
        parsed_url = urlsplit(redirect_url)
    except ValueError:
        raise ComgateError(f"Neplatná adresa brány. Transakce: {transaction_id}.") from None
    allowed_hosts = {"payments.comgate.cz", "pay1.comgate.cz", "pay2.comgate.cz"}
    if parsed_url.scheme != "https" or parsed_url.netloc.lower() not in allowed_hosts:
        raise ComgateError(f"Neočekávaná adresa brány. Transakce: {transaction_id}.")
    return transaction_id, redirect_url


def payment_status(order, transaction_id):
    auth = credentials()
    transaction_id = validate_transaction_id(transaction_id)
    data = request_comgate("GET", f"{API_URL}/transId/{transaction_id}.json", auth, 200)
    if data.get("test") not in (True, "true") or any(
        data.get(field) != expected
        for field, expected in {
            "transId": transaction_id, "refId": order_reference(order), "curr": "CZK",
        }.items()
    ) or str(data.get("price")) != str(order.total_price * 100):
        raise ComgateError("Neshoduje se testovací režim, transakce, reference, částka nebo měna.")
    state = data.get("status")
    if not isinstance(state, str) or state not in STATES:
        raise ComgateError("Comgate vrátila stav mimo rozsah tohoto testu.")
    return state


def apply_test_payment(order):
    if not settings.COMGATE_TEST or settings.EMAIL_TRANSPORT != "preview":
        raise ComgateError("Zpracování testovací platby vyžaduje COMGATE_TEST=true a EMAIL_TRANSPORT=preview.")
    # Serialize local preview processing, including invoice and e-mail logs.
    # SQLite acquires its writer lock on the first write.
    with transaction.atomic():
        matched = Order.objects.filter(
            pk=order.pk,
            course_type=order.course_type,
            created_at=order.created_at,
            total_price=order.total_price,
            status__in=("pending_payment", "paid"),
        ).update(status=F("status"))
        if not matched:
            raise ComgateError("Objednávka se během ověření změnila. Ověřte ji znovu.")

        result = process_order_payment(order.pk)
        if result.errors:
            raise ComgateError(
                "Zpracování platby selhalo a změny byly vráceny. "
                "Zkontrolujte chybový výstup Django a spusťte příkaz znovu."
            )
        invoice_number = result.order.invoice.number

    return result.status_changed, invoice_number
