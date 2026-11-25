from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.db import connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from courses.comgate import process_order_payment
from courses.models import ComgatePayment, EmailLog, Invoice, Order, OrderParticipant


@override_settings(COMGATE_CHECKOUT=True, COMGATE_TEST=True, EMAIL_TRANSPORT="preview")
class ComgateConcurrencyTests(TransactionTestCase):
    def test_concurrent_delivery_and_retry_fulfill_once(self):
        order = Order.objects.create(
            course_type="4", total_price=990, contact_email="payer@example.test",
        )
        OrderParticipant.objects.create(
            order=order, email="student@example.test", first_name="Test", last_name="Student",
        )
        payment = ComgatePayment.objects.create(
            order=order, transaction_id="PAY-CONCURRENT", status=ComgatePayment.Status.PENDING,
        )
        processing = Event()
        release = Event()

        def hold_workflow(order_id):
            processing.set()
            if not release.wait(15):
                raise TimeoutError("The second webhook did not finish.")
            return process_order_payment(order_id)

        def notify():
            try:
                return Client().post(
                    reverse("comgate_webhook"),
                    {"merchant": "test-merchant", "secret": "test-secret",
                     "test": "true", "transId": payment.transaction_id, "status": "PAID"},
                    content_type="application/json",
                ).status_code
            finally:
                connections.close_all()

        with (
            patch.dict("os.environ", COMGATE_MERCHANT_ID="test-merchant", COMGATE_SECRET="test-secret"),
            patch("courses.comgate_views.payment_status", return_value=ComgatePayment.Status.PAID),
            patch("courses.comgate.process_order_payment", side_effect=hold_workflow) as workflow,
            ThreadPoolExecutor(max_workers=2) as workers,
        ):
            first = workers.submit(notify)
            try:
                self.assertTrue(processing.wait(15), "The first webhook did not claim the payment.")
                duplicate = workers.submit(notify)
                self.assertEqual(duplicate.result(timeout=15), 503)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=15), 200)
            self.assertEqual(Client().post(
                reverse("comgate_webhook"),
                {"merchant": "test-merchant", "secret": "test-secret",
                 "test": "true", "transId": payment.transaction_id, "status": "PAID"},
                content_type="application/json",
            ).status_code, 200)
            workflow.assert_called_once_with(order.pk)

        payment.refresh_from_db()
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertIsNone(payment.processing_until)
        invoice = Invoice.objects.get(order=order)
        self.assertTrue(bytes(invoice.pdf_content).startswith(b"%PDF"))
        self.assertCountEqual(
            EmailLog.objects.filter(order=order).values_list("email_type", "status"),
            [
                (EmailLog.TYPE_PAYMENT_COMPLETED, EmailLog.STATUS_PREVIEW),
                (EmailLog.TYPE_PARTICIPANT_ACTIVATION, EmailLog.STATUS_PREVIEW),
            ],
        )
