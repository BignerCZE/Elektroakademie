from django.conf import settings
from django.urls import reverse

from courses.models import Certificate
from courses.services import (
    generate_certificate_pdf,
    generate_quiz_result_pdf,
)

from .renderer import render_email
from .types import EmailAttachment


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
    )




def build_course_completed_email(attempt):
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

    certificate = (
        Certificate.objects
        .select_related(
            "participant",
            "quiz_attempt",
            "quiz_attempt__course",
        )
        .filter(
            participant__user=attempt.user,
            quiz_attempt__course=attempt.course,
        )
        .order_by(
            "-issued_at",
            "-id",
        )
        .first()
    )

    if certificate is None:
        raise ValueError(
            "K úspěšnému testu nebyl nalezen certifikát."
        )

    certificate_pdf = generate_certificate_pdf(
        certificate
    )

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
        subject=(
            "Úspěšné dokončení kurzu – "
            "certifikát a výsledek testu"
        ),
        recipient=attempt.user.email,
        html_template="emails/course_completed.html",
        text_template="emails/course_completed.txt",
        context=context,
        attachments=(
            certificate_attachment,
            quiz_result_attachment,
        ),
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
    )

