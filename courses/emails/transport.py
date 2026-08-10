from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives

from .types import RenderedEmail


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    recipient: str


class PreviewEmailTransport:
    """
    Vývojový transport.

    E-mail skutečně neodesílá. Browser preview se generuje
    samostatně z příslušného builderu.
    """

    def send(
        self,
        email: RenderedEmail,
    ) -> EmailDeliveryResult:
        return EmailDeliveryResult(
            status="preview",
            recipient=email.recipient,
        )


class SMTPEmailTransport:
    """
    Produkční transport využívající standardní Django e-mailový backend.

    Konkrétní SMTP server, port, TLS/SSL a přihlašovací údaje jsou
    definované pouze v Django settings / proměnných prostředí.
    """

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
            from_email=(
                email.from_email
                or settings.DEFAULT_FROM_EMAIL
            ),
            to=[email.recipient],
            reply_to=list(email.reply_to),
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
