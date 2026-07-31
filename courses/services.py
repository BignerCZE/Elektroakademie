from datetime import timedelta
from io import BytesIO

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from .models import (
    Certificate,
    Order,
    OrderParticipant,
    QuizAttempt,
    RegistrationNumberSequence,
)


@transaction.atomic
def generate_registration_number(course_type):
    """
    Vytvoří evidenční číslo například:

    EA-04-202607-00001

    Číselná řada je samostatná pro každý typ kurzu a měsíc.
    """

    now = timezone.localdate()
    course_code = str(course_type).zfill(2)

    sequence, _ = RegistrationNumberSequence.objects.get_or_create(
        course_type=str(course_type),
        year=now.year,
        month=now.month,
        defaults={"last_number": 0},
    )

    sequence = (
        RegistrationNumberSequence.objects
        .select_for_update()
        .get(pk=sequence.pk)
    )

    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])

    return (
        f"EA-{course_code}-"
        f"{now.year}{now.month:02d}-"
        f"{sequence.last_number:05d}"
    )


@transaction.atomic
def mark_order_as_paid(order_id):
    """
    Bezpečně označí objednávku jako zaplacenou a všem jejím
    účastníkům, kteří ještě nemají evidenční číslo, jej přidělí.

    Funkce je idempotentní:
    opakované zavolání nezmění datum zaplacení a nevygeneruje
    účastníkům nová evidenční čísla.
    """

    order = Order.objects.select_for_update().get(pk=order_id)
    status_changed = False

    if order.status != "paid":
        order.status = "paid"
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        status_changed = True

    participants = list(
        order.participants.select_for_update().order_by("id")
    )

    for participant in participants:
        if participant.registration_number:
            continue

        participant.registration_number = generate_registration_number(
            order.course_type
        )
        participant.save(update_fields=["registration_number"])

    return order, participants, status_changed


@transaction.atomic
def generate_certificate(quiz_attempt):
    """
    Vytvoří nebo vrátí osvědčení pro úspěšný odeslaný pokus.

    Platnost osvědčení končí jeden den před třetím výročím
    data vystavení.
    """

    quiz_attempt = (
        QuizAttempt.objects
        .select_for_update()
        .select_related("user", "course")
        .get(pk=quiz_attempt.pk)
    )

    if quiz_attempt.status != QuizAttempt.STATUS_SUBMITTED:
        raise ValueError(
            "Osvědčení lze vytvořit pouze pro odeslaný test."
        )

    if not quiz_attempt.passed:
        raise ValueError(
            "Osvědčení lze vytvořit pouze pro úspěšný test."
        )

    participant = (
        OrderParticipant.objects
        .select_for_update()
        .select_related("order", "profile")
        .filter(
            user=quiz_attempt.user,
            registration_number__isnull=False,
        )
        .exclude(registration_number="")
        .order_by("-activation_completed_at", "-id")
        .first()
    )

    if participant is None:
        raise ValueError(
            "K uživateli nebyl nalezen aktivovaný účastník "
            "s evidenčním číslem."
        )

    issued_at = quiz_attempt.submitted_at or timezone.now()
    valid_until = (
        issued_at.date()
        + relativedelta(years=3)
        - timedelta(days=1)
    )

    certificate, created = Certificate.objects.get_or_create(
        participant=participant,
        defaults={
            "quiz_attempt": quiz_attempt,
            "certificate_number": participant.registration_number,
            "issued_at": issued_at,
            "valid_until": valid_until,
        },
    )

    return certificate, created


def generate_certificate_pdf(certificate):
    """
    Vygeneruje PDF osvědčení v paměti a vrátí jeho obsah jako bytes.

    PDF se neukládá do databáze ani do adresáře media. Stejnou
    funkci lze použít pro stažení, tisk i budoucí přílohu e-mailu.
    """

    certificate = (
        Certificate.objects
        .select_related(
            "participant",
            "participant__user",
            "participant__profile",
            "participant__order",
            "quiz_attempt",
            "quiz_attempt__course",
        )
        .get(pk=certificate.pk)
    )

    participant = certificate.participant
    participant_profile = getattr(
        participant,
        "profile",
        None,
    )
    course = certificate.quiz_attempt.course

    template = get_template(
        "courses/certificate_pdf.html"
    )

    html = template.render({
        "user": participant.user,
        "course": course,
        "certificate": certificate,
        "participant": participant,
        "participant_profile": participant_profile,
        "completion_date": certificate.issued_at,
    })

    result = BytesIO()

    pdf = pisa.CreatePDF(
        src=html,
        dest=result,
        encoding="utf-8",
    )

    if pdf.err:
        raise ValueError(
            "Při generování PDF osvědčení došlo k chybě."
        )

    return result.getvalue()
