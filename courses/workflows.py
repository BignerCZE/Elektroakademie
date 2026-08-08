import logging
from dataclasses import dataclass

from django.conf import settings

from .emails.builders import (
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
from .emails.delivery import deliver_email
from .models import EmailLog, QuizAttempt
from .services import generate_certificate, mark_order_as_paid


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


def process_quiz_completion(attempt):
    """
    Dokončí workflow úspěšně odeslaného testu.

    Vytvoření certifikátu je idempotentní. Závěrečný e-mail se
    posuzuje samostatně podle EmailLog, takže předchozí FAILED stav
    neblokuje další pokus.
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
    # tento pozdější pokus nesmí vytvořit závěrečný e-mail
    # s nesouvisejícím certifikátem.
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
        email = build_course_completed_email(
            attempt
        )
        log = deliver_email(
            email,
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=attempt,
        )
    except Exception as exc:
        logger.exception(
            "Nepodařilo se zpracovat závěrečný e-mail "
            "pro QuizAttempt %s.",
            attempt.pk,
        )
        return QuizCompletionWorkflowResult(
            attempt=attempt,
            certificate=certificate,
            certificate_created=certificate_created,
            email_log=None,
            errors=(str(exc),),
        )

    return QuizCompletionWorkflowResult(
        attempt=attempt,
        certificate=certificate,
        certificate_created=certificate_created,
        email_log=log,
        errors=(),
    )
