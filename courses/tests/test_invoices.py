from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from courses.invoices import issue_invoice, invoice_pdf, render_invoice_html, snapshot_order
from courses.models import Invoice, InvoiceSequence, Order, OrderParticipant, EmailLog
from courses.workflows import process_order_payment


def make_order(**kwargs):
    values = dict(course_type="4", total_price=1980, status="paid", paid_at=timezone.now(),
                  company_name="Žluťoučká firma s.r.o.", street="Dlouhá 123", city="Ostrava",
                  zip_code="70030", country="Česká republika", ico="12345678", dic="CZ12345678",
                  contact_email="kontakt@example.test",
                  invoice_items=[{"description": "§4 – osoba poučená", "quantity": 2, "unit_gross": "990"}])
    values.update(kwargs)
    order = Order.objects.create(**values)
    for index in range(2):
        OrderParticipant.objects.create(order=order, first_name="Jan", last_name="Novák",
                                        email=f"osoba{order.pk}-{index}@example.test")
    return order


@override_settings(EMAIL_TRANSPORT="preview", ALLOWED_HOSTS=["testserver"])
class InvoiceTests(TestCase):
    def test_checkout_ignores_browser_prices_and_grants_only_own_preview(self):
        from courses.tests.test_registration import RegistrationTests
        data = RegistrationTests().get_registration_data()
        data.update(total_price="1", unit_gross="1", invoice_items='[{"quantity":1,"unit_gross":"1"}]')
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.total_price, 990)
        self.assertEqual(order.invoice_items[0]["unit_gross"], "990")
        self.assertEqual(order.invoice_items[0]["quantity"], 1)
        self.assertEqual(self.client.session["invoice_order_ids"], [order.pk])
        preview = self.client.get(reverse("invoice_preview", args=[order.pk]))
        self.assertContains(preview, data["company_name"])
        simulation = self.client.get(reverse("order_payment_simulation", args=[order.pk]))
        self.assertContains(simulation, 'id="payment-countdown">30')
        self.assertNotContains(simulation, reverse("invoice_preview", args=[order.pk]))
        self.assertContains(simulation, 'id="skip-payment-countdown"')
        self.assertContains(simulation, reverse("order_payment_success", args=[order.pk]))
        self.assertFalse(Invoice.objects.exists())
        with patch("courses.workflows.invoice_pdf", return_value=b"%PDF-test"):
            success = self.client.get(reverse("order_payment_success", args=[order.pk]))
        self.assertContains(success, "Aktivační odkazy účastníků")
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

    def test_email_failure_does_not_duplicate_invoice_on_retry(self):
        order = make_order()
        with patch("courses.workflows.invoice_pdf", return_value=b"%PDF-ok"), patch(
                "courses.workflows.deliver_email", side_effect=RuntimeError("email failure")):
            self.assertTrue(process_order_payment(order.pk).errors)
        first = Invoice.objects.get().number
        with patch("courses.workflows.invoice_pdf", return_value=b"%PDF-ok"):
            self.assertFalse(process_order_payment(order.pk).errors)
        self.assertEqual(Invoice.objects.get().number, first)

    def test_annual_sequence_continues_across_months_and_resets_in_prague_new_year(self):
        cases = [
            ("2026-11-01T00:00:00+00:00", "26300001"),
            ("2026-11-05T00:00:00+00:00", "26300002"),
            ("2026-11-30T23:00:00+00:00", "26300003"),
            ("2026-12-31T23:00:00+00:00", "27300001"),
        ]
        for instant, number in cases:
            with patch("courses.invoices.timezone.now", return_value=datetime.fromisoformat(instant)):
                self.assertEqual(issue_invoice(make_order().pk).number, number)

    def test_legacy_monthly_invoice_and_pdf_are_not_renumbered(self):
        order = make_order()
        snapshot = snapshot_order(order)
        legacy = Invoice.objects.create(
            order=order, number="261100042", period="202611", sequence=42,
            issued_on=datetime(2026, 11, 4).date(), snapshot=snapshot,
            pdf_content=b"%PDF-legacy-unchanged",
        )
        InvoiceSequence.objects.create(period="202611", last_number=42)
        with patch("courses.invoices.timezone.now", return_value=datetime.fromisoformat("2026-11-09T10:00:00+00:00")):
            again = issue_invoice(order.pk)
            self.assertEqual(again.pk, legacy.pk)
            self.assertEqual(again.number, "261100042")
            self.assertEqual(invoice_pdf(again), b"%PDF-legacy-unchanged")
            self.assertEqual(InvoiceSequence.objects.count(), 1)
            fresh = issue_invoice(make_order().pk)
        self.assertEqual(fresh.number, "26300001")
        self.assertEqual(fresh.period, "2026")
        self.assertEqual(InvoiceSequence.objects.get(period="202611").last_number, 42)
        legacy.refresh_from_db()
        self.assertEqual(legacy.snapshot, snapshot)

    def test_previous_annual_invoice_keeps_number_and_counter_continues(self):
        order = make_order()
        legacy = Invoice.objects.create(
            order=order, number="2600001", period="2026", sequence=1,
            issued_on=datetime(2026, 11, 4).date(), snapshot=snapshot_order(order),
            pdf_content=b"%PDF-previous-annual-unchanged",
        )
        InvoiceSequence.objects.create(period="2026", last_number=1)
        with patch("courses.invoices.timezone.now", return_value=datetime.fromisoformat("2026-11-09T10:00:00+00:00")):
            again = issue_invoice(order.pk)
            self.assertEqual(again.number, "2600001")
            self.assertEqual(invoice_pdf(again), b"%PDF-previous-annual-unchanged")
            fresh = issue_invoice(make_order().pk)
        self.assertEqual(fresh.number, "26300002")
        self.assertEqual(fresh.sequence, 2)
        self.assertEqual(Invoice.objects.get(pk=legacy.pk).number, "2600001")

    def test_accounting_identifier_and_four_digit_limit(self):
        InvoiceSequence.objects.create(period="2026", last_number=9998)
        with patch("courses.invoices.timezone.now", return_value=datetime.fromisoformat("2026-11-09T10:00:00+00:00")):
            last = issue_invoice(make_order().pk)
            self.assertEqual(last.number, "26309999")
            self.assertEqual(len(last.number), 8)
            self.assertEqual(last.number[2:4], "30")
            with self.assertRaises(ValueError):
                issue_invoice(make_order().pk)
        self.assertEqual(InvoiceSequence.objects.get(period="2026").last_number, 9999)

    def test_idempotent_and_frozen(self):
        order = make_order()
        invoice = issue_invoice(order.pk)
        original = invoice.snapshot
        order.company_name = "Jiná firma"
        order.total_price = 500
        order.invoice_items = []
        order.save()
        order.participants.all().delete()
        again = issue_invoice(order.pk)
        self.assertEqual(again.pk, invoice.pk)
        self.assertEqual(again.snapshot, original)
        self.assertEqual(InvoiceSequence.objects.get().last_number, 1)
        self.assertEqual(original["buyer"]["company_name"], "Žluťoučká firma s.r.o.")
        self.assertEqual(original["items"][0]["quantity"], 2)
        self.assertEqual(original["gross"], "1980.00")
        self.assertEqual(Decimal(original["net"]) + Decimal(original["vat"]), Decimal("1980"))

    def test_unpaid_rejected_without_allocating_number(self):
        with self.assertRaises(ValueError):
            issue_invoice(make_order(status="pending_payment", paid_at=None).pk)
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceSequence.objects.exists())

    def test_legacy_prices_come_from_order_not_current_price_list(self):
        order = make_order(total_price=1800, invoice_items=[])
        self.assertEqual(issue_invoice(order.pk).snapshot["items"][0]["unit_gross"], "900.00")

    def test_inconsistent_items_rollback_counter(self):
        with self.assertRaises(ValueError):
            issue_invoice(make_order(total_price=5).pk)
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceSequence.objects.exists())

    def test_database_enforces_unique_order_number_and_period_sequence(self):
        a = issue_invoice(make_order().pk)
        b = issue_invoice(make_order().pk)
        for field, value in [("number", a.number), ("order_id", a.order_id),
                             ("sequence", a.sequence)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Invoice.objects.filter(pk=b.pk).update(**{field: value})

    def test_overflow_does_not_wrap(self):
        period = timezone.localtime().strftime("%Y")
        InvoiceSequence.objects.create(period=period, last_number=9999)
        with self.assertRaises(ValueError):
            issue_invoice(make_order().pk)
        self.assertFalse(Invoice.objects.exists())

    def test_pdf_failure_retry_and_persisted_bytes(self):
        invoice = issue_invoice(make_order().pk)
        with patch("courses.invoices.generate_html_pdf", side_effect=RuntimeError("PDF failure")):
            with self.assertRaises(RuntimeError):
                invoice_pdf(invoice)
        invoice.refresh_from_db()
        self.assertFalse(invoice.pdf_content)
        with patch("courses.invoices.generate_html_pdf", return_value=b"%PDF-test") as render:
            self.assertEqual(invoice_pdf(invoice), b"%PDF-test")
            self.assertEqual(invoice_pdf(invoice), b"%PDF-test")
            render.assert_called_once()
        self.assertEqual(Invoice.objects.count(), 1)

    def test_invalid_pdf_not_cached(self):
        invoice = issue_invoice(make_order().pk)
        with patch("courses.invoices.generate_html_pdf", return_value=b"bad"):
            with self.assertRaises(ValueError):
                invoice_pdf(invoice)
        invoice.refresh_from_db()
        self.assertFalse(invoice.pdf_content)

    def test_preview_does_not_issue_or_allocate(self):
        order = make_order(status="pending_payment", paid_at=None)
        session = self.client.session
        session["invoice_order_ids"] = [order.pk]
        session.save()
        response = self.client.get(reverse("invoice_preview", args=[order.pk]))
        self.assertContains(response, "NÁHLED PŘED VYSTAVENÍM")
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceSequence.objects.exists())

    def test_owner_foreign_and_staff_permissions(self):
        order, other = make_order(), make_order()
        invoice = issue_invoice(order.pk)
        Invoice.objects.filter(pk=invoice.pk).update(pdf_content=b"%PDF-cached")
        url = reverse("invoice_download", args=[order.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        session = self.client.session
        session["invoice_order_ids"] = [order.pk]
        session.save()
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("invoice_preview", args=[other.pk])).status_code, 404)
        self.client.logout()
        user = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 404)
        user.user_permissions.add(Permission.objects.get(codename="view_invoice"))
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(url)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get(reverse("admin:courses_invoice_changelist")).status_code, 200)

    def test_pdf_endpoint_failure_then_retry(self):
        order = make_order()
        issue_invoice(order.pk)
        session = self.client.session
        session["invoice_order_ids"] = [order.pk]
        session.save()
        url = reverse("invoice_download", args=[order.pk])
        with patch("courses.invoices.generate_html_pdf", side_effect=RuntimeError()):
            self.assertEqual(self.client.get(url).status_code, 503)
        with patch("courses.invoices.generate_html_pdf", return_value=b"%PDF-ok"):
            self.assertEqual(self.client.get(url).content, b"%PDF-ok")
        self.assertEqual(Invoice.objects.count(), 1)

    def test_workflow_defers_payment_email_until_pdf_retry(self):
        order = make_order(status="pending_payment", paid_at=None)
        with patch("courses.workflows.invoice_pdf", side_effect=RuntimeError("PDF failure")):
            first = process_order_payment(order.pk)
        self.assertTrue(first.errors)
        self.assertFalse(EmailLog.objects.filter(email_type=EmailLog.TYPE_PAYMENT_COMPLETED).exists())
        number = Invoice.objects.get().number
        with patch("courses.workflows.invoice_pdf", return_value=b"%PDF-ok"), patch(
                "courses.workflows.deliver_email", wraps=__import__("courses.emails.delivery", fromlist=["deliver_email"]).deliver_email) as delivery:
            second = process_order_payment(order.pk)
            self.assertFalse(second.errors)
            payment_email = delivery.call_args_list[-1].args[0]
            self.assertEqual(payment_email.attachments[0].filename, f"faktura-{number}.pdf")
            self.assertEqual(payment_email.attachments[0].content, b"%PDF-ok")
            process_order_payment(order.pk)
            self.assertEqual(delivery.call_count, 1)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_html_escapes_buyer_and_long_values(self):
        order = make_order(company_name='<script>alert(1)</script>' + 'Žluťoučký ' * 20)
        html = render_invoice_html(issue_invoice(order.pk))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_real_pdf_diacritics_logo_and_multiple_pages(self):
        items = [{"description": f"§4 – osoba poučená, položka {i}", "quantity": 1,
                  "unit_gross": "990"} for i in range(30)]
        order = make_order(total_price=29700, invoice_items=items,
                           company_name="Žluťoučký kůň " * 16, street="Příliš žluťoučká ulice " * 8)
        invoice = issue_invoice(order.pk)
        content = invoice_pdf(invoice)
        reader = PdfReader(BytesIO(content))
        self.assertGreaterEqual(len(reader.pages), 2)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn("Žluťoučký", text)
        self.assertIn("Neplaťte, již uhrazeno", text)
        self.assertIn("29700,00", text.replace("\u00a0", "").replace("\u202f", "").replace(" ", ""))
        self.assertIn("položka 29", text)
        self.assertIn("Označení dodávky", reader.pages[1].extract_text())


class InvoiceConcurrencyTests(TransactionTestCase):
    def test_concurrent_same_and_different_orders(self):
        orders = [make_order() for _ in range(5)]
        ids = [orders[0].pk] * 4 + [o.pk for o in orders[1:]]
        barrier = Barrier(8)
        def run(order_id):
            close_old_connections()
            barrier.wait(timeout=10)
            try:
                return issue_invoice(order_id).number
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, ids))
        self.assertEqual(len(set(results[:4])), 1)
        self.assertEqual(Invoice.objects.count(), 5)
        self.assertEqual(InvoiceSequence.objects.get().last_number, 5)
        self.assertEqual(list(Invoice.objects.order_by("sequence").values_list("sequence", flat=True)), [1,2,3,4,5])
