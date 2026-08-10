# Elektroakademie – Environment Configuration 1.0

## Lokální vývoj

1. Zkopírujte `.env.example` jako `.env`.
2. Do `.env` vložte skutečný `DJANGO_SECRET_KEY`.
3. Pro současný vývoj ponechte `EMAIL_TRANSPORT=preview`.
4. `.env` se nesmí commitovat.

Vygenerování nového Django SECRET_KEY:

    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

## Produkce na PythonAnywhere

Doporučený produkční soubor:

    /home/<uzivatel>/.elektroakademie.env

Nastavte mu oprávnění pouze pro vlastní účet:

    chmod 600 /home/<uzivatel>/.elektroakademie.env

Ve WSGI konfiguraci nastavte před importem Django aplikace:

    import os
    os.environ["ELEKTROAKADEMIE_ENV_FILE"] = "/home/<uzivatel>/.elektroakademie.env"

Produkční soubor pak může obsahovat například:

    DJANGO_SECRET_KEY=<produkční tajný klíč>
    DJANGO_DEBUG=False
    SITE_URL=https://bignercze.pythonanywhere.com

    EMAIL_TRANSPORT=smtp
    EMAIL_HOST=<smtp server>
    EMAIL_PORT=587
    EMAIL_HOST_USER=<smtp uživatel>
    EMAIL_HOST_PASSWORD=<smtp heslo>
    EMAIL_USE_TLS=True
    EMAIL_USE_SSL=False
    DEFAULT_FROM_EMAIL=Elektroakademie <noreply@example.cz>
    SERVER_EMAIL=Elektroakademie <noreply@example.cz>
    EMAIL_TIMEOUT=20

Nikdy necommitujte `.env`, produkční env soubor, SMTP heslo ani DJANGO_SECRET_KEY.
