from django.db import transaction
from django.utils import timezone

from .models import RegistrationNumberSequence


@transaction.atomic
def generate_registration_number(course_type):
    """
    Vytvoří evidenční číslo například:

    EA-04-202607-00001

    Číselná řada je samostatná pro každý typ kurzu a měsíc.
    """

    now = timezone.localdate()

    course_code = str(course_type).zfill(2)

    sequence, created = (
        RegistrationNumberSequence.objects.get_or_create(
            course_type=str(course_type),
            year=now.year,
            month=now.month,
            defaults={
                "last_number": 0,
            },
        )
    )

    sequence = (
        RegistrationNumberSequence.objects
        .select_for_update()
        .get(pk=sequence.pk)
    )

    sequence.last_number += 1
    sequence.save(
        update_fields=["last_number"]
    )

    return (
        f"EA-{course_code}-"
        f"{now.year}{now.month:02d}-"
        f"{sequence.last_number:05d}"
    )