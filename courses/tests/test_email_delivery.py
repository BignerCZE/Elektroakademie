from unittest.mock import patch

from django.test import TestCase, override_settings

from courses.emails.delivery import deliver_email
from courses.emails.transport import EmailDeliveryResult
from courses.emails.types import RenderedEmail
from courses.models import EmailLog, Order


class EmailDeliveryTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
        )

        self.email = RenderedEmail(
            subject="Testovací e-mail",
            recipient="jan@example.com",
            text_body="Textová verze",
            html_body="<p>HTML verze</p>",
        )

    @override_settings(
        EMAIL_TRANSPORT="preview",
    )
    def test_preview_delivery_creates_email_log(self):
        log = deliver_email(
            self.email,
            email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            order=self.order,
        )

        self.assertEqual(
            EmailLog.objects.count(),
            1,
        )

        self.assertEqual(
            log.status,
            EmailLog.STATUS_PREVIEW,
        )

        self.assertEqual(
            log.recipient,
            "jan@example.com",
        )

        self.assertEqual(
            log.subject,
            "Testovací e-mail",
        )

        self.assertEqual(
            log.order,
            self.order,
        )

        self.assertIsNone(
            log.sent_at,
        )

    @override_settings(
        EMAIL_TRANSPORT="preview",
    )
    def test_preview_delivery_does_not_store_email_body(self):
        deliver_email(
            self.email,
            email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            order=self.order,
        )

        log = EmailLog.objects.get()

        self.assertFalse(
            hasattr(log, "html_body")
        )

        self.assertFalse(
            hasattr(log, "text_body")
        )

    @patch(
        "courses.emails.delivery.send_email"
    )
    def test_sent_delivery_sets_sent_at(
        self,
        mock_send_email,
    ):
        mock_send_email.return_value = (
            EmailDeliveryResult(
                status="sent",
                recipient="jan@example.com",
            )
        )

        log = deliver_email(
            self.email,
            email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            order=self.order,
        )

        self.assertEqual(
            log.status,
            EmailLog.STATUS_SENT,
        )

        self.assertIsNotNone(
            log.sent_at,
        )

    @patch(
        "courses.emails.delivery.send_email"
    )
    def test_transport_error_creates_failed_log(
        self,
        mock_send_email,
    ):
        mock_send_email.side_effect = RuntimeError(
            "SMTP není dostupné"
        )

        with self.assertRaises(RuntimeError):
            deliver_email(
                self.email,
                email_type=(
                    EmailLog.TYPE_PAYMENT_COMPLETED
                ),
                order=self.order,
            )

        log = EmailLog.objects.get()

        self.assertEqual(
            log.status,
            EmailLog.STATUS_FAILED,
        )

        self.assertEqual(
            log.error_message,
            "SMTP není dostupné",
        )

        self.assertIsNone(
            log.sent_at,
        )

    @patch(
        "courses.emails.delivery.send_email"
    )
    def test_unknown_delivery_status_raises_error(
        self,
        mock_send_email,
    ):
        mock_send_email.return_value = (
            EmailDeliveryResult(
                status="unknown",
                recipient="jan@example.com",
            )
        )

        with self.assertRaises(ValueError):
            deliver_email(
                self.email,
                email_type=(
                    EmailLog.TYPE_PAYMENT_COMPLETED
                ),
                order=self.order,
            )