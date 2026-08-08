import logging
from dataclasses import dataclass

from django.conf import settings

from .emails.builders import (
    COURSE_COMPLETED_SUBJECT,
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
from .emails.delivery import (
    deliver_email,
    record_email_failure,
)
from .models import EmailLog, QuizAttempt
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


def _completed_email_statuses():
    """
    V preview režimu je náhled považovaný za dokončené zpracování,
    aby opakované spuštění workflow nevytvářelo duplicitní logy.

    Po budoucím přepnutí na skutečný transport se PREVIEW log
    nepovažuje za odeslaný. Staré náhledy tak nebudou blokovat
    první skutečné odeslání přes SMTP.
    """
    transport_name = getattr(
        settings,
        "EMAIL_TRANSPORT",
        "preview",
    )

    if transport_name == "preview":
        return (
            EmailLog.STATUS_PREVIEW,
            EmailLog.STATUS_SENT,
        )

    return (EmailLog.STATUS_SENT,)


def _email_already_completed(**filters):
    return EmailLog.objects.filter(
        status__in=_completed_email_statuses(),
        **filters,
    ).exists()


def process_order_payment(order_id):
    """
    Kompletní workflow po přijetí platby.

    Platba a evidenční čísla jsou řešeny existující službou.
    E-mailové kroky se následně reconciliují i pro již zaplacenou
    objednávku, takže workflow umí opravit dříve nedokončený krok.
    """
    order, participants, status_changed = mark_order_as_paid(
        order_id
    )
    participants = tuple(participants)
    errors = []

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

    if not _email_already_completed(
        **payment_log_filters
    ):
        try:
            email = build_payment_completed_email(
                order,
                participants,
            )
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


def _record_course_completion_failure(
    attempt,
    error_message,
):
    return record_email_failure(
        email_type=EmailLog.TYPE_COURSE_COMPLETED,
        recipient=attempt.user.email,
        subject=COURSE_COMPLETED_SUBJECT,
        error=error_message,
        quiz_attempt=attempt,
    )


def process_quiz_completion(attempt):
    """
    Dokončí workflow úspěšně odeslaného testu.

    Jednotlivé kroky jsou idempotentní na úrovni výsledného
    e-mailového workflow:

    1. vytvoření / načtení certifikátu,
    2. PDF certifikátu,
    3. PDF výsledku testu,
    4. sestavení závěrečného e-mailu,
    5. předání aktivnímu transportu,
    6. záznam výsledku do EmailLog.

    PREVIEW/SENT záznam další běh zastaví. FAILED záznam další
    pokus neblokuje, takže je možné bezpečně opravit dočasné
    selhání generování PDF nebo e-mailového transportu.
    """
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

    log_filters = {
        "email_type": EmailLog.TYPE_COURSE_COMPLETED,
        "quiz_attempt": attempt,
        "recipient": attempt.user.email,
    }

    if _email_already_completed(**log_filters):
        return QuizCompletionWorkflowResult(
            attempt=attempt,
            certificate=certificate,
            certificate_created=certificate_created,
            email_log=None,
            errors=(),
        )

    try:
        certificate_pdf = _validate_pdf_content(
            generate_certificate_pdf(certificate),
            "PDF certifikátu",
        )
        quiz_result_pdf = _validate_pdf_content(
            generate_quiz_result_pdf(attempt),
            "PDF výsledku testu",
        )

        email = build_course_completed_email(
            attempt,
            certificate=certificate,
            certificate_pdf=certificate_pdf,
            quiz_result_pdf=quiz_result_pdf,
        )

    except Exception as exc:
        error_message = (
            "Příprava závěrečného e-mailu selhala: "
            f"{exc}"
        )
        _record_course_completion_failure(
            attempt,
            error_message,
        )
        logger.exception(
            "Nepodařilo se připravit závěrečný e-mail "
            "pro QuizAttempt %s.",
            attempt.pk,
        )
        return QuizCompletionWorkflowResult(
            attempt=attempt,
            certificate=certificate,
            certificate_created=certificate_created,
            email_log=None,
            errors=(error_message,),
        )

    try:
        log = deliver_email(
            email,
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=attempt,
        )
    except Exception as exc:
        # deliver_email zapisuje FAILED záznam samo, takže zde
        # chybu pouze vracíme volajícímu a nevytváříme duplicitu.
        error_message = (
            "Doručení závěrečného e-mailu selhalo: "
            f"{exc}"
        )
        logger.exception(
            "Nepodařilo se doručit závěrečný e-mail "
            "pro QuizAttempt %s.",
            attempt.pk,
        )
        return QuizCompletionWorkflowResult(
            attempt=attempt,
            certificate=certificate,
            certificate_created=certificate_created,
            email_log=None,
            errors=(error_message,),
        )

    return QuizCompletionWorkflowResult(
        attempt=attempt,
        certificate=certificate,
        certificate_created=certificate_created,
        email_log=log,
        errors=(),
    )
