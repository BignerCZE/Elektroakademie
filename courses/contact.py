import logging
from datetime import timedelta
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_email
from django.db import DatabaseError
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .emails.transport import send_email, smtp_enabled_for
from .emails.types import RenderedEmail
from .models import ContactRateLimit

logger = logging.getLogger(__name__)

CONTACT_TOPICS = (
    ("obecne-informace", "Obecné informace"),
    ("paragraf-4", "§4 – osoba poučená"),
    ("paragraf-6", "§6 – elektrotechnik"),
    ("paragraf-7", "§7 – vedoucí elektrotechnik"),
    ("individualni-skoleni", "Individuální školení"),
    ("firemni-skoleni", "Firemní školení"),
)
TURNSTILE_ACTION = "contact"
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
UNAVAILABLE = "Kontaktní formulář je dočasně nedostupný. Zkuste to prosím později."
CAPTCHA_UNAVAILABLE = "Ověření CAPTCHA je dočasně nedostupné. Zkuste to prosím později."
SUCCESS_SESSION_KEY = "contact_sent"


class ContactForm(forms.Form):
    name = forms.CharField(
        label="Jméno", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Vaše jméno", "autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="E-mail", max_length=254,
        widget=forms.EmailInput(attrs={"placeholder": "vas@email.cz", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Telefon", required=False, max_length=32,
        widget=forms.TextInput(attrs={
            "type": "tel", "placeholder": "+420 123 456 789", "autocomplete": "tel",
        }),
        validators=[RegexValidator(
            r"\A(?=(?:[^0-9]*[0-9]){3})[0-9+(). /-]+\Z",
            message="Zadejte platné telefonní číslo.",
        )],
    )
    topic = forms.ChoiceField(label="Předmět", choices=CONTACT_TOPICS)
    message = forms.CharField(
        label="Zpráva", max_length=5000,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Napište nám zprávu"}),
    )


def contact_available():
    if not settings.TURNSTILE_SITE_KEY or not settings.TURNSTILE_SECRET_KEY:
        return False
    try:
        validate_email(settings.CONTACT_EMAIL_RECIPIENT)
        validate_email(settings.CONTACT_FROM_EMAIL)
    except ValidationError:
        return False
    return smtp_enabled_for(settings.CONTACT_EMAIL_RECIPIENT)


def contact_client_address(request):
    # Only use the peer address supplied by the server. Forwarded headers
    # are unsafe here unless the deployment explicitly establishes trust.
    try:
        address = ip_address(request.META.get("REMOTE_ADDR", ""))
        if address.version == 6:
            address = address.ipv4_mapped or ip_network(f"{address}/64", strict=False)
    except ValueError:
        address = "unknown"

    return str(address)


def within_rate_limit(scope, identity, limit):
    now = timezone.now().replace(microsecond=0)
    window = 600
    epoch = int(now.timestamp())
    bucket = salted_hmac(
        "contact.rate-limit", f"{scope}:{identity}:{epoch // window}", algorithm="sha256",
    ).hexdigest()
    expires_at = now + timedelta(seconds=window - (epoch % window))
    entries = ContactRateLimit.objects
    _, created = entries.get_or_create(bucket=bucket, defaults={"expires_at": expires_at})
    if created:
        entries.filter(expires_at__lte=now).delete()
        return True
    return bool(entries.filter(bucket=bucket, attempts__lt=limit).update(attempts=F("attempts") + 1))


class TurnstileUnavailable(Exception):
    pass


def turnstile_error(token):
    if not token:
        return "Dokončete prosím ověření CAPTCHA."
    if len(token) > 2048:
        return "Ověření CAPTCHA se nezdařilo. Zopakujte ho prosím."

    try:
        response = requests.post(
            TURNSTILE_URL,
            data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token},
            timeout=(3, 5),
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise TurnstileUnavailable
        result = response.json()
    except (requests.RequestException, ValueError):
        raise TurnstileUnavailable from None

    if not isinstance(result, dict):
        raise TurnstileUnavailable
    if result.get("success") is True:
        if (
            result.get("hostname") == urlsplit(settings.SITE_URL).hostname
            and result.get("action") == TURNSTILE_ACTION
        ):
            return ""
        return "Ověření CAPTCHA se nezdařilo. Zopakujte ho prosím."

    errors = result.get("error-codes")
    if result.get("success") is not False or not isinstance(errors, list):
        raise TurnstileUnavailable
    if any(code in errors for code in ("internal-error", "missing-input-secret", "invalid-input-secret", "bad-request")):
        raise TurnstileUnavailable
    if "timeout-or-duplicate" in errors:
        return "Ověření CAPTCHA vypršelo nebo už bylo použito. Zopakujte ho prosím."
    return "Ověření CAPTCHA se nezdařilo. Zopakujte ho prosím."


def submit_contact(request, form):
    if not contact_available():
        return UNAVAILABLE, 503

    limited = "Bylo odesláno příliš mnoho požadavků. Zkuste to prosím za několik minut.", 429
    try:
        if not within_rate_limit("address", contact_client_address(request), 30):
            return limited
        if not form.is_valid():
            return "Zkontrolujte prosím označená pole.", 400
        if not within_rate_limit("email", form.cleaned_data["email"].casefold(), 5):
            return limited
    except DatabaseError:
        logger.warning("Omezení četnosti kontaktního formuláře je nedostupné.")
        return UNAVAILABLE, 503

    try:
        error = turnstile_error(request.POST.get("cf-turnstile-response", "").strip())
    except TurnstileUnavailable:
        return CAPTCHA_UNAVAILABLE, 503
    if error:
        return error, 400

    data = form.cleaned_data
    email = RenderedEmail(
        subject=f"Elektroakademie – {dict(CONTACT_TOPICS)[data['topic']]}",
        recipient=settings.CONTACT_EMAIL_RECIPIENT,
        from_email=settings.CONTACT_FROM_EMAIL,
        reply_to=(data["email"],),
        text_body=(
            f"Jméno: {data['name']}\nE-mail: {data['email']}\n"
            f"Telefon: {data['phone'] or 'Neuveden'}\n\n{data['message']}"
        ),
        html_body="",
    )
    try:
        if send_email(email).status == "sent":
            return "", 200
    except Exception as exc:
        logger.warning("Odeslání kontaktní zprávy selhalo (%s).", type(exc).__name__)

    return "Zprávu se nepodařilo odeslat. Zkuste to prosím znovu.", 503
