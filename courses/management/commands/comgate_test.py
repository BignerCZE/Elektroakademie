from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from courses.comgate import (
    ComgateError, apply_test_payment, create_payment, order_reference, payment_status,
)
from courses.models import ComgatePayment, Order

STATES = {
    "PENDING": "Platba čeká na dokončení.",
    "PAID": "Comgate potvrdila úspěšnou testovací platbu.",
    "CANCELLED": "Testovací platba byla zrušena.",
}


class Command(BaseCommand):
    help = "Založí, ověří nebo lokálně zpracuje testovací platbu Comgate pro § 4."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        create = actions.add_parser("create", help="Založí testovací platbu.")
        create.add_argument("order_id", type=int)
        status = actions.add_parser("status", help="Ověří stav testovací platby.")
        status.add_argument("order_id", type=int)
        status.add_argument("transaction_id")
        apply = actions.add_parser("apply", help="Zpracuje ověřenou testovací platbu v režimu preview.")
        apply.add_argument("order_id", type=int)
        apply.add_argument("transaction_id")

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.COMGATE_TEST:
            raise CommandError("Příkaz vyžaduje DJANGO_DEBUG=True a COMGATE_TEST=true.")

        action = options["action"]
        if action == "apply" and settings.EMAIL_TRANSPORT != "preview":
            raise CommandError("Zpracování testovací platby vyžaduje EMAIL_TRANSPORT=preview.")

        try:
            order = Order.objects.get(pk=options["order_id"], course_type="4")
        except Order.DoesNotExist:
            raise CommandError("Objednávka kurzu § 4 nebyla nalezena.") from None

        price = order.total_price * 100
        currency = "CZK"
        try:
            if action == "create":
                if ComgatePayment.objects.filter(order=order).exists():
                    raise CommandError("Tato objednávka už používá platbu založenou z checkoutu.")
                if order.status != "pending_payment" or not 100 <= price <= 100_000_000:
                    raise CommandError("Objednávka musí čekat na platbu a mít částku 1 až 1 000 000 Kč.")
                if not order.contact_email or not order.contact_full_name:
                    raise CommandError("Lokální objednávka musí mít kontaktní jméno a e-mail.")
                return_url = f"http://127.0.0.1:8000/platba/{order.pk}/"
                transaction_id, redirect_url = create_payment(order, return_url)
                self.stdout.write(f"transId: {transaction_id}")
                self.stdout.write(f"URL: {redirect_url}")
            else:
                state = payment_status(order, options["transaction_id"])
                self.stdout.write(f"{state}: {STATES[state]}")
                if action == "apply" and state == "PAID":
                    if ComgatePayment.objects.filter(order=order).exists():
                        raise CommandError("Platbu založenou z checkoutu zpracujte přes webhook.")
                    changed, number = apply_test_payment(order)
                    if changed:
                        self.stdout.write(
                            f"Objednávka označena jako zaplacená. Faktura {number}, e-maily v režimu preview."
                        )
                    else:
                        self.stdout.write(f"Objednávka už byla zaplacená. Faktura {number}.")
        except ComgateError as exc:
            raise CommandError(str(exc)) from None

        self.stdout.write(f"Objednávka #{order.pk}, refId: {order_reference(order)}, price: {price}, curr: {currency}")
