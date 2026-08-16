import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SMTP_HOST = os.getenv("EMAIL_HOST", "").strip()
SMTP_PORT = int(os.getenv("EMAIL_PORT", "587"))
SMTP_USERNAME = os.getenv("EMAIL_HOST_USER", "").strip()
SMTP_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

USE_TLS = env_bool("EMAIL_USE_TLS", True)
USE_SSL = env_bool("EMAIL_USE_SSL", False)

ALIASES = [
    ("Aktivace", os.getenv("EMAIL_FROM_ACTIVATION", "").strip()),
    ("Faktury", os.getenv("EMAIL_FROM_INVOICES", "").strip()),
    ("Osvědčení", os.getenv("EMAIL_FROM_CERTIFICATES", "").strip()),
]


def validate_config():
    missing = []

    if not SMTP_HOST:
        missing.append("EMAIL_HOST")
    if not SMTP_USERNAME:
        missing.append("EMAIL_HOST_USER")
    if not SMTP_PASSWORD:
        missing.append("EMAIL_HOST_PASSWORD")

    for label, address in ALIASES:
        if not address:
            missing.append(f"alias {label}")

    if USE_TLS and USE_SSL:
        raise SystemExit(
            "CHYBA: EMAIL_USE_TLS a EMAIL_USE_SSL nemohou být současně True."
        )

    if missing:
        raise SystemExit(
            "CHYBA: Chybí konfigurace: " + ", ".join(missing)
        )


def connect():
    context = ssl.create_default_context()

    if USE_SSL:
        smtp = smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
            context=context,
        )
    else:
        smtp = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        )
        smtp.ehlo()

        if USE_TLS:
            smtp.starttls(context=context)
            smtp.ehlo()

    smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
    return smtp


def build_message(label, from_email, to_email):
    msg = EmailMessage()
    msg["Subject"] = f"Elektroakademie – SMTP test aliasu {label}"
    msg["From"] = from_email
    msg["To"] = to_email

    msg.set_content(
        f"""Test SMTP aliasu Elektroakademie.

Typ: {label}
From: {from_email}
SMTP účet: {SMTP_USERNAME}

Pokud zpráva dorazila, zkontroluj:
- zobrazeného odesílatele,
- hlavičku From,
- případně Return-Path / Sender.
"""
    )
    return msg


def main():
    validate_config()

    print("SMTP TEST ALIASŮ ELEKTROAKADEMIE")
    print("=" * 42)
    print(f"SMTP server: {SMTP_HOST}:{SMTP_PORT}")
    print(f"SMTP účet:   {SMTP_USERNAME}")
    print(f"TLS:         {USE_TLS}")
    print(f"SSL:         {USE_SSL}")
    print()

    to_email = input(
        "Zadej e-mail, na který mají přijít testovací zprávy: "
    ).strip()

    if not to_email or "@" not in to_email:
        raise SystemExit("CHYBA: Neplatná cílová e-mailová adresa.")

    smtp = None

    try:
        print("\nPřipojuji se k SMTP...")
        smtp = connect()
        print("Přihlášení k SMTP: OK\n")

        for label, from_email in ALIASES:
            msg = build_message(label, from_email, to_email)

            print(f"Testuji {label}: {from_email}")

            try:
                refused = smtp.send_message(
                    msg,
                    from_addr=from_email,
                    to_addrs=[to_email],
                )

                if refused:
                    print("  CHYBA: server odmítl příjemce:", refused)
                else:
                    print("  SMTP přijal zprávu: OK")

            except smtplib.SMTPException as exc:
                print(f"  SMTP CHYBA: {type(exc).__name__}: {exc}")

            except Exception as exc:
                print(f"  CHYBA: {type(exc).__name__}: {exc}")

            print()

    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass

    print("=" * 42)
    print("Test dokončen.")
    print("Zkontroluj doručené zprávy a jejich hlavičky.")


if __name__ == "__main__":
    main()
