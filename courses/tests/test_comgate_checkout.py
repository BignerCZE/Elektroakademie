from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from courses.comgate import order_reference
from courses.models import ComgatePayment, EmailLog, Invoice, Order


@override_settings(COMGATE_CHECKOUT=True, COMGATE_TEST=True, EMAIL_TRANSPORT="preview")
class ComgateCheckoutTests(TestCase):
    def setUp(self):
        self.webhook = reverse("comgate_webhook")
        self.response = self.enterContext(patch("courses.comgate.requests.request")).return_value
        self.enterContext(patch.dict("os.environ", COMGATE_MERCHANT_ID="test-merchant", COMGATE_SECRET="test-secret"))
        self.pdf = self.enterContext(patch("courses.invoices.generate_html_pdf", return_value=b"%PDF-test"))

    def create_order(self):
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
        response = self.client.post(reverse("register"), data)
        self.assertRedirects(response, self.response.json.return_value["redirect"], fetch_redirect_response=False)
        order = Order.objects.get()
        return order, order.comgate_payment

    def notify(self, payment, state, **overrides):
        payload = {
            "merchant": "test-merchant", "secret": "test-secret", "test": "true",
            "transId": payment.transaction_id, "status": state, **overrides,
        }
        return Client(enforce_csrf_checks=True).post(self.webhook, payload, content_type="application/json")

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
