from dataclasses import dataclass

from django.conf import settings

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


def get_email_transport():
    transport_name = getattr(
        settings,
        "EMAIL_TRANSPORT",
        "preview",
    )

    if transport_name == "preview":
        return PreviewEmailTransport()

    raise ValueError(
        f"Neznámý e-mailový transport: {transport_name}"
    )


def send_email(
    email: RenderedEmail,
) -> EmailDeliveryResult:
    transport = get_email_transport()

    return transport.send(email)