from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from courses.comgate import order_reference
from courses.comgate_views import checkout_available
from courses.emails.transport import send_email
from courses.models import ComgatePayment, EmailLog, Invoice, Order


@override_settings(COMGATE_CHECKOUT=True, COMGATE_TEST=True, EMAIL_TRANSPORT="preview")
class ComgateCheckoutTests(TestCase):
    def setUp(self):
        self.webhook = reverse("comgate_webhook")
        self.api_request = self.enterContext(patch("courses.comgate.requests.request"))
        self.response = self.api_request.return_value
        self.enterContext(patch.dict("os.environ", COMGATE_MERCHANT_ID="test-merchant", COMGATE_SECRET="test-secret"))
        self.pdf = self.enterContext(patch("courses.invoices.generate_html_pdf", return_value=b"%PDF-test"))

    def create_order(self, *, secure=False):
        from .test_registration_order_controls import RegistrationOrderControlsTests

        data = RegistrationOrderControlsTests().get_registration_data()
        data.update({
            "participants-TOTAL_FORMS": "2",
            "participants-1-first_name": "Druhy",
            "participants-1-last_name": "Ucastnik",
            "participants-1-email": "druhy@example.com",
        })
        self.response.status_code = 201
        self.response.json.return_value = {
            "code": 0, "transId": "PAY1-TEST-0001",
            "redirect": "https://pay1.comgate.cz/init?id=PAY1-TEST-0001",
        }
        response = self.client.post(reverse("register"), data, secure=secure)
        self.assertRedirects(response, self.response.json.return_value["redirect"], fetch_redirect_response=False)
        order = Order.objects.get()
        return order, order.comgate_payment

    def notify(self, payment, state, *, secure=False, **overrides):
        payload = {
            "merchant": "test-merchant", "secret": "test-secret", "test": "true",
            "transId": payment.transaction_id, "status": state, **overrides,
        }
        return Client(enforce_csrf_checks=True).post(
            self.webhook, payload, content_type="application/json", secure=secure,
        )

    def api_status(self, order, payment, state, **overrides):
        self.response.status_code = 200
        self.response.json.return_value = {
            "code": 0, "test": "true", "transId": payment.transaction_id, "refId": order_reference(order),
            "curr": "CZK", "price": "198000", "status": state, **overrides,
        }

    def test_checkout_webhook_and_duplicate_confirmation(self):
        order, payment = self.create_order()
        request_api = self.response.json
        self.assertEqual(request_api.call_count, 1)
        self.assertEqual(order.total_price, 1980)
        self.assertEqual(payment.status, "PENDING")
        result_url = reverse("comgate_result", args=[order.pk])
        self.assertContains(self.client.get(result_url + "?status=PAID"), "Čekáme na potvrzení platby.")
        self.assertEqual(Client().get(result_url).status_code, 404)
        self.assertEqual(self.client.get(reverse("order_payment_success", args=[order.pk])).status_code, 404)
        self.assertEqual(self.notify(payment, "PAID", secret="invalid").status_code, 403)

        self.api_status(order, payment, "PENDING")
        self.assertEqual(self.notify(payment, "PAID").status_code, 503)
        self.api_status(order, payment, "PAID", price="99000")
        self.assertEqual(self.notify(payment, "PAID").status_code, 503)
        self.assertFalse(Invoice.objects.exists())

        self.api_status(order, payment, "PAID")
        for _ in range(2):
            self.assertEqual(self.notify(payment, "PAID").status_code, 200)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, "PAID")
        self.assertEqual(order.status, "paid")
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)
        self.assertEqual(EmailLog.objects.filter(order=order, status="preview").count(), 3)
        self.assertEqual(self.pdf.call_count, 1)
        self.assertContains(self.client.get(result_url), "Objednávka je zaplacená.")

    @override_settings(
        COMGATE_TEST=True, COMGATE_LIVE=False, EMAIL_TRANSPORT="smtp_test",
        EMAIL_TEST_RECIPIENTS=("jan.novak@example.com", "kontakt@example.com"),
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        SITE_URL="https://elektroakademie.cz",
        EMAIL_FROM_ACTIVATION="aktivace@elektroakademie.cz",
        EMAIL_FROM_INVOICES="faktury@elektroakademie.cz",
    )
    def test_test_payment_webhook_sends_only_allowlisted_application_mail(self):
        order, payment = self.create_order()
        self.assertIs(self.api_request.call_args.kwargs["json"]["test"], True)
        self.api_status(order, payment, "PAID")
        for _ in range(2):
            self.assertEqual(self.notify(payment, "PAID").status_code, 200)
        payment.refresh_from_db()
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertEqual(EmailLog.objects.get(order=order, status="preview").recipient, "druhy@example.com")
        messages = {message.to[0]: message for message in mail.outbox}
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(set(messages), {"jan.novak@example.com", "kontakt@example.com"})
        activation = messages["jan.novak@example.com"]
        self.assertEqual(activation.from_email, "aktivace@elektroakademie.cz")
        self.assertIn("https://elektroakademie.cz/", activation.body)
        invoice = messages["kontakt@example.com"]
        self.assertEqual(invoice.from_email, "faktury@elektroakademie.cz")
        attachment, = invoice.attachments
        self.assertTrue(attachment.filename.startswith("faktura-"))
        self.assertEqual(attachment.mimetype, "application/pdf")
        self.assertEqual(attachment.content, b"%PDF-test")

    def test_test_checkout_requires_a_safe_email_mode(self):
        for settings_override in (
            {"EMAIL_TRANSPORT": "smtp"},
            {"EMAIL_TRANSPORT": "smtp_test", "EMAIL_TEST_RECIPIENTS": ()},
            {
                "EMAIL_TRANSPORT": "smtp_test",
                "EMAIL_TEST_RECIPIENTS": ("jan.novak@example.com",),
                "COMGATE_LIVE": True,
            },
        ):
            with self.subTest(**settings_override), self.settings(**settings_override):
                self.assertFalse(checkout_available())

    def test_cancelled_payment_does_not_fulfill_order(self):
        order, payment = self.create_order()
        self.api_status(order, payment, "CANCELLED")
        self.assertEqual(self.notify(payment, "CANCELLED").status_code, 200)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, "CANCELLED")
        self.assertEqual(order.status, "pending_payment")
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(EmailLog.objects.exists())


    @override_settings(
        DEBUG=False, COMGATE_TEST=False, COMGATE_LIVE=True,
        EMAIL_TRANSPORT="smtp", EMAIL_HOST="localhost",
        DEFAULT_FROM_EMAIL="test@example.com",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_URL="https://testserver",
    )
    def test_live_mode_keeps_completed_email_steps_after_failure(self):
        order, payment = self.create_order(secure=True)
        self.assertIs(payment.is_test, False)
        self.assertIs(self.api_request.call_args.kwargs["json"]["test"], False)
        result_url = reverse("comgate_result", args=[order.pk])
        self.assertContains(
            self.client.get(result_url + "?status=PAID", secure=True),
            "Čekáme na potvrzení platby.",
        )
        self.assertEqual(self.notify(payment, "PAID", secure=True).status_code, 403)
        self.api_status(order, payment, "PAID")
        self.assertEqual(self.notify(payment, "PAID", secure=True, test="false").status_code, 503)
        self.assertFalse(Invoice.objects.exists())

        self.api_status(order, payment, "PAID", test="false")
        failed = set()

        def deliver(email):
            if email.recipient == "druhy@example.com" and not failed:
                failed.add(email.recipient)
                raise ConnectionError("Test SMTP rejection")
            return send_email(email)

        with patch("courses.emails.delivery.send_email", side_effect=deliver):
            with self.assertLogs("courses.workflows", level="ERROR"):
                self.assertEqual(self.notify(payment, "PAID", secure=True, test="false").status_code, 503)
            invoice = Invoice.objects.get(order=order)
            self.assertEqual(len(mail.outbox), 2)
            for _ in range(2):
                self.assertEqual(self.notify(payment, "PAID", secure=True, test="false").status_code, 200)

        payment.refresh_from_db()
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertEqual(Invoice.objects.get(order=order).pk, invoice.pk)
        self.assertCountEqual(
            [message.to[0] for message in mail.outbox],
            ["druhy@example.com", "jan.novak@example.com", "kontakt@example.com"],
        )

    @override_settings(COMGATE_CHECKOUT=False, PAYMENT_SIMULATION=False)
    def test_public_deployment_disables_legacy_simulation(self):
        for name in ("order_payment_simulation", "order_payment_success"):
            self.assertEqual(self.client.get(reverse(name, args=[1])).status_code, 404)


    def test_second_worker_waits_for_active_processing(self):
        order, payment = self.create_order()
        payment.processing_until = timezone.now() + timedelta(minutes=10)
        payment.save(update_fields=["processing_until"])
        self.api_status(order, payment, "PAID")
        self.assertEqual(self.notify(payment, "PAID").status_code, 503)
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(EmailLog.objects.exists())
