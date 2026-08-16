import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from courses.emails.builders import build_payment_completed_email
from courses.emails.transport import send_email
from courses.models import Order


def build_django_message(email):
    message = EmailMultiAlternatives(
        subject=email.subject,
        body=email.text_body,
        from_email=(
            email.from_email
            or settings.DEFAULT_FROM_EMAIL
        ),
        to=[email.recipient],
        reply_to=list(email.reply_to),
    )

    if email.html_body:
        message.attach_alternative(
            email.html_body,
            "text/html",
        )

    for attachment in email.attachments:
        message.attach(
            attachment.filename,
            attachment.content,
            attachment.mimetype,
        )

    return message


def main():
    print("=" * 70)
    print("DIAGNOSTIKA POTVRZENÍ PLATBY – ELEKTROAKADEMIE")
    print("=" * 70)

    value = input("ID objednávky [14]: ").strip()
    order_id = int(value or "14")

    order = Order.objects.get(pk=order_id)
    participants = tuple(order.participants.all())

    email = build_payment_completed_email(
        order,
        participants,
    )

    print()
    print("OBJEDNÁVKA")
    print(f"ID:             {order.pk}")
    print(f"Stav:           {order.status}")
    print(f"Kontaktní mail: {order.contact_email}")
    print(f"Účastníků:      {len(participants)}")

    print()
    print("RENDERED EMAIL")
    print(f"Subject:        {email.subject}")
    print(f"To:             {email.recipient}")
    print(f"From:           {email.from_email!r}")
    print(f"Reply-To:       {email.reply_to!r}")
    print(f"Text délka:     {len(email.text_body)}")
    print(f"HTML délka:     {len(email.html_body)}")
    print(f"Příloh:         {len(email.attachments)}")

    print()
    print("SMTP / DJANGO SETTINGS")
    print(f"EMAIL_TRANSPORT: {settings.EMAIL_TRANSPORT}")
    print(f"EMAIL_BACKEND:   {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST:      {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT:      {settings.EMAIL_PORT}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_USE_TLS:   {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_USE_SSL:   {settings.EMAIL_USE_SSL}")
    print(f"DEFAULT_FROM:    {settings.DEFAULT_FROM_EMAIL}")
    print(
        "FROM_INVOICES:   "
        f"{getattr(settings, 'EMAIL_FROM_INVOICES', None)}"
    )

    message = build_django_message(email)

    print()
    print("VÝSLEDNÉ HLAVIČKY DJANGO ZPRÁVY")
    print(f"From:      {message.from_email}")
    print(f"To:        {message.to}")
    print(f"Reply-To:  {message.reply_to}")
    print(f"Subject:   {message.subject}")

    mime = message.message()

    print()
    print("MIME")
    print(f"Content-Type: {mime.get_content_type()}")
    print(f"Multipart:    {mime.is_multipart()}")

    if mime.is_multipart():
        print("Části:")
        for index, part in enumerate(mime.walk(), start=1):
            if part.is_multipart():
                continue

            print(
                f"  {index}: "
                f"{part.get_content_type()} "
                f"| encoding={part.get('Content-Transfer-Encoding')}"
            )

    print()
    print("DŮLEŽITÉ HLAVIČKY PŘED ODESLÁNÍM")
    for name in (
        "From",
        "To",
        "Subject",
        "Reply-To",
        "Message-ID",
        "Date",
    ):
        print(f"{name}: {mime.get(name)}")

    print()
    answer = input(
        "Odeslat tuto zprávu přes skutečný SMTP transport? [a/N]: "
    ).strip().lower()

    if answer not in {"a", "ano", "y", "yes"}:
        print("Neodesláno.")
        return

    print()
    print("Odesílám přes courses.emails.transport.send_email()...")

    result = send_email(email)

    print()
    print("=" * 70)
    print("VÝSLEDEK")
    print(f"Status:    {result.status}")
    print(f"Recipient: {result.recipient}")
    print("=" * 70)
    print(
        "Pokud SMTP vrátí 'sent', zkontroluj fyzické doručení "
        "do stejné schránky jako u sendmail.py."
    )


if __name__ == "__main__":
    main()
