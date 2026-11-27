import logging
from time import monotonic, sleep
from dataclasses import dataclass, replace

from django.conf import settings
from django.db import connection, OperationalError, transaction
from django.db.models import F

from .emails.builders import (
    COURSE_COMPLETED_SUBJECT,
    ORDER_CONTACT_COURSE_COMPLETED_SUBJECT,
    build_order_contact_course_completed_email,
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
from .emails.delivery import (
    deliver_email,
    record_email_failure,
)
from .models import EmailLog, Order, QuizAttempt
from .invoices import issue_invoice, invoice_pdf
from .emails.types import EmailAttachment
from .emails.transport import smtp_enabled_for
from .services import (
    generate_certificate,
    generate_certificate_pdf,
    generate_quiz_result_pdf,
    mark_order_as_paid,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderPaymentWorkflowResult:
    order: object
    participants: tuple
    status_changed: bool
    errors: tuple


@dataclass(frozen=True)
class QuizCompletionWorkflowResult:
    attempt: object
    certificate: object
    certificate_created: bool
    email_log: object
    errors: tuple


def _email_already_completed(**filters):
    statuses = [EmailLog.STATUS_SENT]
    if settings.EMAIL_TRANSPORT in {"preview", "smtp_test"} and not smtp_enabled_for(filters["recipient"]):
        statuses.append(EmailLog.STATUS_PREVIEW)
    return EmailLog.objects.filter(status__in=statuses, **filters).exists()


def _mark_order_paid_serialized(order_id):
    # Acquire SQLite's writer lock before mark_order_as_paid reads the order.
    deadline = monotonic() + 5
    while True:
        acquired = False
        try:
            with transaction.atomic():
                Order.objects.filter(pk=order_id).update(status=F("status"))
                acquired = True
                result = mark_order_as_paid(order_id)
            return result
        except OperationalError as exc:
            if (acquired or connection.vendor != "sqlite"
                    or "locked" not in str(exc).lower() or monotonic() >= deadline):
                raise
            sleep(0.01)


def process_order_payment(order_id):
    """
    Kompletní workflow po přijetí platby.

    Platba a evidenční čísla jsou řešeny existující službou.
    E-mailové kroky se následně reconciliují i pro již zaplacenou
    objednávku, takže workflow umí opravit dříve nedokončený krok.
    """
    order, participants, status_changed = _mark_order_paid_serialized(
        order_id
    )
    participants = tuple(participants)
    errors = []
    invoice_attachment = None
    try:
        invoice = issue_invoice(order.pk)
        invoice_attachment = EmailAttachment(
            filename=f"faktura-{invoice.number}.pdf",
            content=invoice_pdf(invoice), mimetype="application/pdf",
        )
    except Exception as exc:
        errors.append(f"Faktura objednávky {order.pk}: {exc}")
        logger.exception("Příprava faktury selhala pro objednávku %s", order.pk)

    for participant in participants:
        log_filters = {
            "email_type": EmailLog.TYPE_PARTICIPANT_ACTIVATION,
            "order": order,
            "recipient": participant.email,
        }

        if _email_already_completed(**log_filters):
            continue

        try:
            email = build_participant_activation_email(
                participant
            )
            log = deliver_email(
                email,
                email_type=(
                    EmailLog.TYPE_PARTICIPANT_ACTIVATION
                ),
                order=order,
            )

            if (
                log.status == EmailLog.STATUS_SENT
                and participant.activation_sent_at is None
            ):
                participant.activation_sent_at = log.sent_at
                participant.save(
                    update_fields=["activation_sent_at"]
                )

        except Exception as exc:
            errors.append(
                (
                    "Aktivační e-mail pro účastníka "
                    f"{participant.pk}: {exc}"
                )
            )
            logger.exception(
                "Nepodařilo se zpracovat aktivační e-mail "
                "pro účastníka %s.",
                participant.pk,
            )

    payment_log_filters = {
        "email_type": EmailLog.TYPE_PAYMENT_COMPLETED,
        "order": order,
        "recipient": order.contact_email,
    }

    if invoice_attachment is not None and not _email_already_completed(
        **payment_log_filters
    ):
        try:
            email = build_payment_completed_email(
                order,
                participants,
            )
            email = replace(email, attachments=(*email.attachments, invoice_attachment))
            deliver_email(
                email,
                email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
                order=order,
            )
        except Exception as exc:
            errors.append(
                (
                    "Potvrzení platby pro objednávku "
                    f"{order.pk}: {exc}"
                )
            )
            logger.exception(
                "Nepodařilo se zpracovat potvrzení o přijetí "
                "platby pro objednávku %s.",
                order.pk,
            )

    return OrderPaymentWorkflowResult(
        order=order,
        participants=participants,
        status_changed=status_changed,
        errors=tuple(errors),
    )


def _validate_pdf_content(content, label):
    if not isinstance(content, (bytes, bytearray)):
        raise ValueError(
            f"{label} nebylo vygenerováno jako binární PDF."
        )

    content = bytes(content)

    if not content.startswith(b"%PDF"):
        raise ValueError(
            f"{label} nemá platnou PDF hlavičku."
        )

    return content


def process_quiz_completion(attempt):
    """Send each completion email independently and skip completed deliveries."""
    attempt = (
        QuizAttempt.objects
        .select_related("user", "course")
        .get(pk=attempt.pk)
    )

    if attempt.status != QuizAttempt.STATUS_SUBMITTED:
        raise ValueError(
            "Workflow dokončení kurzu vyžaduje odeslaný test."
        )

    if not attempt.passed:
        raise ValueError(
            "Workflow dokončení kurzu vyžaduje úspěšný test."
        )

    certificate, certificate_created = generate_certificate(
        attempt
    )

    # Současný model dovoluje účastníkovi právě jeden certifikát.
    # Pokud už existuje certifikát navázaný na jiný pokus,
    # tento pozdější pokus nesmí pracovat s nesouvisejícím
    # certifikátem.
    if certificate.quiz_attempt_id != attempt.pk:
        return QuizCompletionWorkflowResult(
            attempt=attempt,
            certificate=certificate,
            certificate_created=certificate_created,
            email_log=None,
            errors=(),
        )

    order = certificate.participant.order
    contact_email = order.contact_email.strip()
    deliveries = [
        (EmailLog.TYPE_COURSE_COMPLETED, attempt.user.email, COURSE_COMPLETED_SUBJECT),
    ]
    if order.status == "paid" and contact_email and contact_email.casefold() != attempt.user.email.strip().casefold():
        deliveries.append((
            EmailLog.TYPE_ORDER_CONTACT_COURSE_COMPLETED,
            contact_email,
            ORDER_CONTACT_COURSE_COMPLETED_SUBJECT,
        ))

    pending = [
        (email_type, recipient, subject)
        for email_type, recipient, subject in deliveries
        if not _email_already_completed(email_type=email_type, recipient=recipient, quiz_attempt=attempt)
    ]
    errors = []
    participant_log = None
    certificate_pdf = None
    if pending:
        try:
            certificate_pdf = _validate_pdf_content(
                generate_certificate_pdf(certificate), "PDF certifikátu",
            )
        except Exception as exc:
            error_message = f"Příprava závěrečného e-mailu selhala: {exc}"
            logger.exception("Příprava PDF certifikátu selhala pro QuizAttempt %s.", attempt.pk)
            for email_type, recipient, subject in pending:
                record_email_failure(
                    email_type=email_type, recipient=recipient, subject=subject,
                    error=error_message, quiz_attempt=attempt,
                    order=order if email_type == EmailLog.TYPE_ORDER_CONTACT_COURSE_COMPLETED else None,
                )
            errors.append(error_message)
            pending = []

    for email_type, recipient, subject in pending:
        is_participant = email_type == EmailLog.TYPE_COURSE_COMPLETED
        log_context = {"quiz_attempt": attempt}
        if not is_participant:
            log_context["order"] = order
        try:
            if is_participant:
                quiz_result_pdf = _validate_pdf_content(
                    generate_quiz_result_pdf(attempt), "PDF výsledku testu",
                )
                email = build_course_completed_email(
                    attempt, certificate=certificate, certificate_pdf=certificate_pdf,
                    quiz_result_pdf=quiz_result_pdf,
                )
            else:
                email = build_order_contact_course_completed_email(certificate, order, certificate_pdf)
        except Exception as exc:
            error_message = f"Příprava závěrečného e-mailu selhala: {exc}"
            record_email_failure(
                email_type=email_type, recipient=recipient, subject=subject,
                error=error_message, **log_context,
            )
            logger.exception("Příprava e-mailu %s selhala pro QuizAttempt %s.", email_type, attempt.pk)
            errors.append(error_message)
            continue

        try:
            log = deliver_email(email, email_type=email_type, **log_context)
            if is_participant:
                participant_log = log
        except Exception as exc:
            logger.exception("Odeslání e-mailu %s selhalo pro QuizAttempt %s.", email_type, attempt.pk)
            errors.append(f"Odeslání závěrečného e-mailu selhalo: {exc}")

    return QuizCompletionWorkflowResult(
        attempt=attempt,
        certificate=certificate,
        certificate_created=certificate_created,
        email_log=participant_log,
        errors=tuple(errors),
    )
