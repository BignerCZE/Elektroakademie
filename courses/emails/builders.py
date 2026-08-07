from django.conf import settings
from django.urls import reverse

from .renderer import render_email


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
        "course_name": participant.order.get_course_type_display(),
        "activation_url": activation_url,
    }

    return render_email(
        subject="Aktivace přístupu do Elektroakademie",
        recipient=participant.email,
        html_template="emails/participant_activation.html",
        text_template="emails/participant_activation.txt",
        context=context,
    )

def build_order_confirmation_email(order):
    participants = list(
        order.participants.all()
    )

    context = {
        "order": order,
        "participants": participants,
        "course_name": order.get_course_type_display(),
    }

    return render_email(
        subject=f"Potvrzení objednávky č. {order.id} – Elektroakademie",
        recipient=order.contact_email,
        html_template="emails/order_confirmation.html",
        text_template="emails/order_confirmation.txt",
        context=context,
    )