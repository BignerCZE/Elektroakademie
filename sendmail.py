import smtplib
from email.message import EmailMessage

# ==========================================
# SMTP konfigurace
# ==========================================

SMTP_HOST = "wes1-smtp.wedos.net"
SMTP_PORT = 587
SMTP_USERNAME = "elektroakademie@revitec.cz"
SMTP_PASSWORD = "Qwer1234."

USE_TLS = True

# ==========================================
# Testovaný alias
# ==========================================

FROM_EMAIL = "faktury@elektroakademie.cz"

# Kam se odešle test
TO_EMAIL = "test-faktury@elektroakademie.cz"

# ==========================================
# Vytvoření zprávy
# ==========================================

msg = EmailMessage()
msg["Subject"] = "SMTP test aliasu"
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL

msg.set_content(
    """Toto je testovací e-mail.

Pokud jej čteš, SMTP funguje.

Odesílatel:
{}
""".format(FROM_EMAIL)
)

# ==========================================
# Odeslání
# ==========================================

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:

        if USE_TLS:
            smtp.starttls()

        smtp.login(
            SMTP_USERNAME,
            SMTP_PASSWORD,
        )

        smtp.send_message(msg)

    print("===================================")
    print("E-mail byl úspěšně odeslán.")
    print(f"FROM: {FROM_EMAIL}")
    print(f"TO:   {TO_EMAIL}")
    print("===================================")

except Exception as exc:
    print("===================================")
    print("Chyba při odeslání:")
    print(exc)
    print("===================================")