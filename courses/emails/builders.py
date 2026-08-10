from django.conf import settings
from django.urls import reverse

from courses.models import Certificate
from courses.services import (
    generate_certificate_pdf,
    generate_quiz_result_pdf,
)

from .renderer import render_email
from .types import EmailAttachment


def _reply_to():
    value = getattr(
        settings,
        "EMAIL_REPLY_TO",
        "",
    ).strip()

    if not value:
        return ()

    return (value,)


def build_participant_activation_email(participant):
    activation_path = reverse(
        "participant_activation",
        kwargs={
            "token": participant.activation_token,
        },
    )
    activation_url = (
        f"{settings.SITE_URL}{activation_path}"
    )

    context = {
        "participant": participant,
        "order": participant.order,
        "course_name": (
            participant.order.get_course_type_display()
        ),
        "activation_url": activation_url,
    }

    return render_email(
        subject="Aktivace přístupu do Elektroakademie",
        recipient=participant.email,
        html_template="emails/participant_activation.html",
        text_template="emails/participant_activation.txt",
        context=context,
        from_email=settings.EMAIL_FROM_ACTIVATION,
        reply_to=_reply_to(),
    )


COURSE_COMPLETED_SUBJECT = (
    "Úspěšné dokončení kurzu – "
    "certifikát a výsledek testu"
)


def build_course_completed_email(
    attempt,
    *,
    certificate=None,
    certificate_pdf=None,
    quiz_result_pdf=None,
):
    """
    Sestaví závěrečný e-mail.

    Pokud PDF přílohy nejsou předané, vygeneruje je builder sám.
    To zachovává funkčnost administrátorských preview view.
    Workflow dokončení kurzu naopak předává již připravené PDF,
    aby bylo možné každý krok samostatně zachytit a auditovat.
    """
    if attempt.status != attempt.STATUS_SUBMITTED:
        raise ValueError(
            "Závěrečný e-mail lze vytvořit pouze "
            "pro odeslaný test."
        )

    if not attempt.passed:
        raise ValueError(
            "Závěrečný e-mail lze vytvořit pouze "
            "pro úspěšně dokončený test."
        )

    if certificate is None:
        certificate = (
            Certificate.objects
            .select_related(
                "participant",
                "quiz_attempt",
                "quiz_attempt__course",
            )
            .filter(
                quiz_attempt=attempt,
            )
            .first()
        )

    if certificate is None:
        raise ValueError(
            "K úspěšnému testu nebyl nalezen certifikát."
        )

    if certificate.quiz_attempt_id != attempt.pk:
        raise ValueError(
            "Certifikát nepatří k zadanému testovému pokusu."
        )

    if certificate_pdf is None:
        certificate_pdf = generate_certificate_pdf(
            certificate
        )

    if quiz_result_pdf is None:
        quiz_result_pdf = generate_quiz_result_pdf(
            attempt
        )

    certificate_attachment = EmailAttachment(
        filename=(
            f"certifikat-"
            f"{certificate.certificate_number}.pdf"
        ),
        content=certificate_pdf,
        mimetype="application/pdf",
    )

    quiz_result_attachment = EmailAttachment(
        filename=(
            f"vysledek-testu-"
            f"{attempt.id}.pdf"
        ),
        content=quiz_result_pdf,
        mimetype="application/pdf",
    )

    context = {
        "attempt": attempt,
        "user": attempt.user,
        "course": attempt.course,
        "certificate": certificate,
    }

    return render_email(
        subject=COURSE_COMPLETED_SUBJECT,
        recipient=attempt.user.email,
        html_template="emails/course_completed.html",
        text_template="emails/course_completed.txt",
        context=context,
        attachments=(
            certificate_attachment,
            quiz_result_attachment,
        ),
        from_email=settings.EMAIL_FROM_CERTIFICATES,
        reply_to=_reply_to(),
    )


def build_payment_completed_email(
    order,
    participants,
):
    context = {
        "order": order,
        "participants": participants,
        "course_name": order.get_course_type_display(),
    }

    return render_email(
        subject=(
            "Platba přijata – účastníci mohou zahájit studium"
        ),
        recipient=order.contact_email,
        html_template="emails/payment_completed.html",
        text_template="emails/payment_completed.txt",
        context=context,
        from_email=settings.EMAIL_FROM_INVOICES,
        reply_to=_reply_to(),
    )
