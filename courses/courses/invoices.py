"""Immutable invoice snapshots; no transport or payment gateway calls."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from zoneinfo import ZoneInfo
import time

from django.db import OperationalError, transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Invoice, InvoiceSequence, Order
from .services import generate_html_pdf, load_static_data_uri

PRAGUE = ZoneInfo("Europe/Prague")
SELLER = {
    "name": "Revitec elektro s.r.o.", "street": "Zenklova 24/54",
    "city": "Praha", "zip_code": "180 00", "country": "Česká republika",
    "ico": "24944769", "dic": "CZ24944769",
    "phone": "+420 777 002 043", "email": "info@elektroakademie.cz",
    "bank": "Raiffeisenbank a.s.", "account": "81072355/5500",
    "iban": "CZ4755000000000081072355", "swift": "RZBCCZPP",
}


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def snapshot_order(order):
    raw = order.invoice_items
    if not raw:
        # Legacy orders have a server-calculated total, but no saved line prices.
        count = order.participants.count()
        if count < 1:
            raise ValueError("Objednávka nemá účastníky.")
        unit = Decimal(order.total_price) / count
        if money(unit) * count != money(order.total_price):
            raise ValueError("Nelze přesně odvodit jednotkovou cenu starší objednávky.")
        raw = [{"description": order.get_course_type_display(),
                "quantity": count, "unit_gross": str(money(unit))}]
    items = []
    for line in raw:
        qty = line["quantity"]
        if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
            raise ValueError("Neplatné množství položky.")
        unit = money(line["unit_gross"])
        if not unit.is_finite() or unit < 0:
            raise ValueError("Neplatná jednotková cena.")
        gross = money(unit * qty)
        net = money(gross / Decimal("1.21"))
        items.append({"description": line["description"], "quantity": qty,
                      "unit_gross": str(unit), "unit_net": str(money(unit / Decimal("1.21"))),
                      "net": str(net), "vat": str(gross - net), "gross": str(gross)})
    total = sum((Decimal(i["gross"]) for i in items), Decimal(0))
    if total != money(order.total_price):
        raise ValueError("Položky nesouhlasí s uloženou cenou objednávky.")
    return {
        "version": 1, "seller": SELLER.copy(),
        "buyer": {key: getattr(order, key) for key in
                  ("company_name", "street", "city", "zip_code", "country", "ico", "dic")},
        "order_id": order.pk,
        "ordered_on": timezone.localtime(order.created_at, PRAGUE).date().isoformat(),
        "paid_on": timezone.localtime(order.paid_at, PRAGUE).date().isoformat() if order.paid_at else None,
        "items": items, "gross": str(total),
        "net": str(sum((Decimal(i["net"]) for i in items), Decimal(0))),
        "vat": str(sum((Decimal(i["vat"]) for i in items), Decimal(0))),
        "vat_rate": 21, "payment_method": "Platební brána", "constant_symbol": "0308",
        "logo": load_static_data_uri("courses/img/svetle_pozadi_bez_sloganu.svg", "image/svg+xml"),
    }


def issue_invoice(order_id):
    """First write obtains SQLite's write lock BEFORE reading state.

    No PDF/email side effects in the transaction. A failed attempt rolls back
    completely. Bounded retries also support SQLite shared-cache test databases.
    """
    for attempt in range(30):
        try:
            with transaction.atomic():
                Order.objects.filter(pk=order_id).update(total_price=F("total_price"))
                order = Order.objects.select_for_update().get(pk=order_id)
                existing = Invoice.objects.filter(order=order).first()
                if existing:
                    return existing
                if order.status != "paid" or not order.paid_at:
                    raise ValueError("Fakturu lze vystavit pouze zaplacené objednávce.")
                issued = timezone.localtime(timezone.now(), PRAGUE).date()
                period = issued.strftime("%Y")
                counter, _ = InvoiceSequence.objects.get_or_create(period=period)
                counter = InvoiceSequence.objects.select_for_update().get(pk=counter.pk)
                if counter.last_number >= 99999:
                    raise ValueError("Roční číselná řada je vyčerpána.")
                snapshot = snapshot_order(order)
                counter.last_number += 1
                counter.save(update_fields=["last_number"])
                return Invoice.objects.create(
                    order=order, number=issued.strftime("%y") + f"{counter.last_number:05d}",
                    period=period, sequence=counter.last_number, issued_on=issued, snapshot=snapshot,
                )
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 29:
                raise
            time.sleep(min(0.01 * (attempt + 1), 0.1))


def render_invoice_html(invoice=None, *, order=None):
    if invoice is None:
        data = snapshot_order(order)
        issued = timezone.localtime(timezone.now(), PRAGUE).date()
    else:
        data, issued = invoice.snapshot, invoice.issued_on
    font_regular = load_static_data_uri("courses/fonts/NotoSans-Regular.ttf", "font/ttf")
    font_bold = load_static_data_uri("courses/fonts/NotoSans-Bold.ttf", "font/ttf")
    return render_to_string("courses/invoice.html", {
        "data": data, "invoice": invoice, "issued": issued,
        "font_regular": font_regular, "font_bold": font_bold,
        "ordered_on": date.fromisoformat(data["ordered_on"]),
        "paid_on": date.fromisoformat(data["paid_on"]) if data["paid_on"] else None,
    })


def invoice_pdf(invoice):
    invoice = Invoice.objects.get(pk=invoice.pk)
    cached = invoice.pdf_content
    if cached:
        return bytes(cached)
    content = generate_html_pdf(render_invoice_html(invoice))
    if not isinstance(content, bytes) or not content.startswith(b"%PDF"):
        raise ValueError("Generování nevrátilo platné PDF.")
    # Concurrent renders may finish together: only the first complete PDF wins.
    Invoice.objects.filter(pk=invoice.pk, pdf_content=b"").update(pdf_content=content)
    return bytes(Invoice.objects.get(pk=invoice.pk).pdf_content)
