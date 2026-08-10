from pathlib import Path
import re

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "CHYBA: Skript spusťte z kořene projektu Elektroakademie "
        "(adresář s manage.py)."
    )

transport_path = ROOT / "courses" / "emails" / "transport.py"
settings_path = ROOT / "config" / "settings.py"
test_path = ROOT / "courses" / "tests" / "test_smtp_transport.py"

for path in (transport_path, settings_path):
    if not path.exists():
        raise SystemExit(f"CHYBA: Nenalezen očekávaný soubor: {path}")

NEW_TRANSPORT = """from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives

from .types import RenderedEmail


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    recipient: str


class PreviewEmailTransport:
    \"\"\"
    Vývojový transport.

    E-mail skutečně neodesílá. Browser preview se generuje
    samostatně z příslušného builderu.
    \"\"\"

    def send(
        self,
        email: RenderedEmail,
    ) -> EmailDeliveryResult:
        return EmailDeliveryResult(
            status="preview",
            recipient=email.recipient,
        )


class SMTPEmailTransport:
    \"\"\"
    Produkční transport využívající standardní Django e-mailový backend.

    Konkrétní SMTP server, port, TLS/SSL a přihlašovací údaje jsou
    definované pouze v Django settings / proměnných prostředí.
    \"\"\"

    def _validate_configuration(self):
        if not getattr(settings, "EMAIL_HOST", ""):
            raise ImproperlyConfigured(
                "Pro EMAIL_TRANSPORT='smtp' musí být nastaven EMAIL_HOST."
            )

        if not getattr(settings, "DEFAULT_FROM_EMAIL", ""):
            raise ImproperlyConfigured(
                "Pro EMAIL_TRANSPORT='smtp' musí být nastaven "
                "DEFAULT_FROM_EMAIL."
            )

        if (
            getattr(settings, "EMAIL_USE_TLS", False)
            and getattr(settings, "EMAIL_USE_SSL", False)
        ):
            raise ImproperlyConfigured(
                "EMAIL_USE_TLS a EMAIL_USE_SSL nemohou být současně True."
            )

    def send(
        self,
        email: RenderedEmail,
    ) -> EmailDeliveryResult:
        self._validate_configuration()

        message = EmailMultiAlternatives(
            subject=email.subject,
            body=email.text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email.recipient],
        )

        if email.html_body:
            message.attach_alternative(
                email.html_body,
                "text/html",
            )

        for attachment in email.attachments:
            message.attach(
                attachment.filename,
                attachment.content,
                attachment.mimetype,
            )

        sent_count = message.send(
            fail_silently=False,
        )

        if sent_count != 1:
            raise RuntimeError(
                "SMTP transport nepotvrdil odeslání e-mailu "
                f"příjemci {email.recipient}."
            )

        return EmailDeliveryResult(
            status="sent",
            recipient=email.recipient,
        )


def get_email_transport():
    transport_name = getattr(
        settings,
        "EMAIL_TRANSPORT",
        "preview",
    ).strip().lower()

    if transport_name == "preview":
        return PreviewEmailTransport()

    if transport_name == "smtp":
        return SMTPEmailTransport()

    raise ValueError(
        f"Neznámý e-mailový transport: {transport_name}"
    )


def send_email(
    email: RenderedEmail,
) -> EmailDeliveryResult:
    transport = get_email_transport()

    return transport.send(email)
"""

SMTP_SETTINGS = """# -----------------------------------------------------------------------------
# E-mailový transport a SMTP
# -----------------------------------------------------------------------------

EMAIL_TRANSPORT = os.getenv(
    "EMAIL_TRANSPORT",
    "preview",
).strip().lower()

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

EMAIL_USE_TLS = os.getenv(
    "EMAIL_USE_TLS",
    "True",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

EMAIL_USE_SSL = os.getenv(
    "EMAIL_USE_SSL",
    "False",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

EMAIL_TIMEOUT = int(
    os.getenv(
        "EMAIL_TIMEOUT",
        "20",
    )
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "webmaster@localhost",
)

SERVER_EMAIL = os.getenv(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
)
"""

NEW_TEST = """from unittest.mock import patch

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
"""

old_transport = transport_path.read_text(encoding="utf-8")
settings_text = settings_path.read_text(encoding="utf-8")

required_transport_markers = (
    "class PreviewEmailTransport:",
    "def get_email_transport():",
    "def send_email(",
)
if not all(marker in old_transport for marker in required_transport_markers):
    raise SystemExit(
        "CHYBA: courses/emails/transport.py neodpovídá očekávané "
        "architektuře. Skript nic nezměnil."
    )

if "class SMTPEmailTransport:" in old_transport:
    print("INFO: SMTP transport již v transport.py existuje; ponechávám jej.")
else:
    transport_path.write_text(NEW_TRANSPORT, encoding="utf-8")

if "# E-mailový transport a SMTP" in settings_text:
    print("INFO: SMTP blok v settings.py již existuje; ponechávám jej.")
else:
    pattern = re.compile(
        r'(?ms)^EMAIL_TRANSPORT\s*=\s*os\.getenv\(\s*'
        r'["\\\']EMAIL_TRANSPORT["\\\']\s*,\s*'
        r'["\\\']preview["\\\']\s*,?\s*\)'
        r'(?:\.strip\(\)\.lower\(\))?\s*$'
    )
    match = pattern.search(settings_text)

    if not match:
        # Fallback: locate the assignment by line and consume the complete
        # parenthesized expression, independent of whitespace/newline style.
        start = re.search(
            r'(?m)^EMAIL_TRANSPORT\s*=\s*os\.getenv\(',
            settings_text,
        )
        if not start:
            raise SystemExit(
                "CHYBA: EMAIL_TRANSPORT nebyl v config/settings.py nalezen. "
                "Skript nic nezměnil."
            )

        pos = start.start()
        open_paren = settings_text.find("(", start.start())
        depth = 0
        end = None
        for i in range(open_paren, len(settings_text)):
            ch = settings_text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end is None:
            raise SystemExit(
                "CHYBA: Nepodařilo se bezpečně určit konec EMAIL_TRANSPORT "
                "konfigurace. Skript nic nezměnil."
            )

        tail = settings_text[end:end + 32]
        lower_suffix = re.match(r'\s*\.strip\(\)\.lower\(\)', tail)
        if lower_suffix:
            end += lower_suffix.end()

        current_block = settings_text[pos:end]
        if (
            '"EMAIL_TRANSPORT"' not in current_block
            and "'EMAIL_TRANSPORT'" not in current_block
        ):
            raise SystemExit(
                "CHYBA: Nalezený EMAIL_TRANSPORT blok není očekávaný "
                "os.getenv blok. Skript nic nezměnil."
            )

        settings_text = (
            settings_text[:pos]
            + SMTP_SETTINGS.rstrip()
            + settings_text[end:]
        )
    else:
        settings_text = (
            settings_text[:match.start()]
            + SMTP_SETTINGS.rstrip()
            + settings_text[match.end():]
        )

    settings_path.write_text(settings_text, encoding="utf-8")

test_path.write_text(NEW_TEST, encoding="utf-8")

print("HOTOVO:")
print(f"  upraveno/ověřeno: {transport_path.relative_to(ROOT)}")
print(f"  upraveno/ověřeno: {settings_path.relative_to(ROOT)}")
print(f"  vytvořeno/aktualizováno: {test_path.relative_to(ROOT)}")
print()
print("Modely ani databázové schéma nebyly změněny; migrace nejsou potřeba.")
print()
print("Spusťte:")
print("  python manage.py test courses.tests.test_smtp_transport")
print("  python manage.py test courses.tests.test_email_delivery")
print("  python manage.py test courses.tests.test_email_flows")
print("  python manage.py test courses")
