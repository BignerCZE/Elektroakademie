from django.utils import timezone

from courses.models import EmailLog

from .transport import send_email
from .types import RenderedEmail


def deliver_email(
    email: RenderedEmail,
    *,
    email_type,
    order=None,
    quiz_attempt=None,
):
    """
    Předá sestavený e-mail aktivnímu transportu
    a zaznamená výsledek do EmailLog.

    Samotný obsah e-mailu ani přílohy se do databáze
    neukládají.
    """

    try:
        result = send_email(email)

    except Exception as exc:
        EmailLog.objects.create(
            email_type=email_type,
            recipient=email.recipient,
            subject=email.subject,
            status=EmailLog.STATUS_FAILED,
            error_message=str(exc),
            order=order,
            quiz_attempt=quiz_attempt,
        )

        raise

    if result.status == "preview":
        status = EmailLog.STATUS_PREVIEW
        sent_at = None

    elif result.status == "sent":
        status = EmailLog.STATUS_SENT
        sent_at = timezone.now()

    else:
        raise ValueError(
            f"Neznámý stav doručení e-mailu: {result.status}"
        )

    log = EmailLog.objects.create(
        email_type=email_type,
        recipient=email.recipient,
        subject=email.subject,
        status=status,
        order=order,
        quiz_attempt=quiz_attempt,
        sent_at=sent_at,
    )

    return log