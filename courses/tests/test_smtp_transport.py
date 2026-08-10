from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from courses.emails.transport import (
    PreviewEmailTransport,
    SMTPEmailTransport,
    get_email_transport,
    send_email,
)
from courses.emails.types import (
    EmailAttachment,
    RenderedEmail,
)


class EmailTransportSelectionTests(SimpleTestCase):
    @override_settings(EMAIL_TRANSPORT="preview")
    def test_preview_transport_is_selected(self):
        self.assertIsInstance(
            get_email_transport(),
            PreviewEmailTransport,
        )

    @override_settings(EMAIL_TRANSPORT="smtp")
    def test_smtp_transport_is_selected(self):
        self.assertIsInstance(
            get_email_transport(),
            SMTPEmailTransport,
        )

    @override_settings(EMAIL_TRANSPORT="invalid")
    def test_unknown_transport_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_email_transport()


@override_settings(
    EMAIL_TRANSPORT="smtp",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="smtp.example.com",
    EMAIL_PORT=587,
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
    DEFAULT_FROM_EMAIL="Elektroakademie <noreply@example.com>",
)
class SMTPEmailTransportTests(SimpleTestCase):
    def setUp(self):
        self.email = RenderedEmail(
            subject="Testovací SMTP e-mail",
            recipient="jan@example.com",
            text_body="Textová verze",
            html_body="<p>HTML verze</p>",
        )

    def test_smtp_transport_sends_multipart_email(self):
        result = send_email(self.email)

        self.assertEqual(result.status, "sent")
        self.assertEqual(result.recipient, "jan@example.com")
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, "Testovací SMTP e-mail")
        self.assertEqual(message.body, "Textová verze")
        self.assertEqual(
            message.from_email,
            "Elektroakademie <noreply@example.com>",
        )
        self.assertEqual(message.to, ["jan@example.com"])
        self.assertEqual(
            message.alternatives[0].content,
            "<p>HTML verze</p>",
        )
        self.assertEqual(
            message.alternatives[0].mimetype,
            "text/html",
        )

    def test_smtp_transport_preserves_pdf_attachments(self):
        email = RenderedEmail(
            subject=self.email.subject,
            recipient=self.email.recipient,
            text_body=self.email.text_body,
            html_body=self.email.html_body,
            attachments=(
                EmailAttachment(
                    filename="certifikat.pdf",
                    content=b"%PDF-certificate",
                    mimetype="application/pdf",
                ),
                EmailAttachment(
                    filename="vysledek.pdf",
                    content=b"%PDF-result",
                    mimetype="application/pdf",
                ),
            ),
        )

        send_email(email)

        message = mail.outbox[0]
        self.assertEqual(len(message.attachments), 2)
        self.assertEqual(
            message.attachments[0].filename,
            "certifikat.pdf",
        )
        self.assertEqual(
            message.attachments[0].mimetype,
            "application/pdf",
        )
        self.assertEqual(
            message.attachments[1].filename,
            "vysledek.pdf",
        )
        self.assertEqual(
            message.attachments[1].mimetype,
            "application/pdf",
        )

    @override_settings(EMAIL_HOST="")
    def test_missing_smtp_host_raises_configuration_error(self):
        with self.assertRaises(ImproperlyConfigured):
            send_email(self.email)

    @override_settings(
        EMAIL_USE_TLS=True,
        EMAIL_USE_SSL=True,
    )
    def test_tls_and_ssl_cannot_be_enabled_together(self):
        with self.assertRaises(ImproperlyConfigured):
            send_email(self.email)

    @patch(
        "courses.emails.transport.EmailMultiAlternatives.send",
        return_value=0,
    )
    def test_unconfirmed_send_raises_runtime_error(
        self,
        mock_send,
    ):
        with self.assertRaises(RuntimeError):
            send_email(self.email)

        mock_send.assert_called_once_with(
            fail_silently=False,
        )
