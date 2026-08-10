from pathlib import Path
import re
import secrets

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "CHYBA: Skript spusťte z kořene projektu Elektroakademie "
        "(adresář s manage.py)."
    )

settings_path = ROOT / "config" / "settings.py"
gitignore_path = ROOT / ".gitignore"
requirements_path = ROOT / "requirements.txt"
env_example_path = ROOT / ".env.example"
env_path = ROOT / ".env"

for path in (settings_path, gitignore_path, requirements_path):
    if not path.exists():
        raise SystemExit(f"CHYBA: Nenalezen očekávaný soubor: {path}")

# 1) requirements.txt
requirements = requirements_path.read_text(encoding="utf-8-sig")

if not re.search(
    r"(?mi)^python-dotenv(?:\s*==\s*[^\s]+)?\s*$",
    requirements,
):
    if requirements and not requirements.endswith("\n"):
        requirements += "\n"
    requirements += "python-dotenv==1.2.2\n"
    requirements_path.write_text(requirements, encoding="utf-8")

# 2) .gitignore
gitignore = gitignore_path.read_text(encoding="utf-8")
lines = gitignore.splitlines()

lines = [
    line
    for line in lines
    if line.strip() not in {
        ".env/",
        ".env",
        ".env.*",
        "!.env.example",
    }
]

while lines and not lines[-1].strip():
    lines.pop()

lines += [
    "",
    "# Environment / secrets",
    ".env",
    ".env.*",
    "!.env.example",
    "",
]

gitignore_path.write_text("\n".join(lines), encoding="utf-8")

# 3) .env.example
ENV_EXAMPLE = '''# =============================================================================
# Elektroakademie - vzor konfigurace prostředí
# Tento soubor neobsahuje žádná skutečná hesla.
# Zkopírujte jej jako .env pouze pro lokální vývoj.
# =============================================================================

# Django
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
SITE_URL=http://127.0.0.1:8000

# E-mailový transport
EMAIL_TRANSPORT=preview

# SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=
EMAIL_TIMEOUT=20
'''

env_example_path.write_text(ENV_EXAMPLE, encoding="utf-8")

# 4) config/settings.py
settings = settings_path.read_text(encoding="utf-8")

if "from dotenv import load_dotenv" not in settings:
    settings = settings.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\n\n"
        "from django.core.exceptions import ImproperlyConfigured\n"
        "from dotenv import load_dotenv\n",
        1,
    )
elif "from django.core.exceptions import ImproperlyConfigured" not in settings:
    settings = settings.replace(
        "from dotenv import load_dotenv\n",
        "from django.core.exceptions import ImproperlyConfigured\n"
        "from dotenv import load_dotenv\n",
        1,
    )

ENV_LOADER = '''BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Proměnné prostředí / secrets
# -----------------------------------------------------------------------------

ENV_FILE = os.getenv("ELEKTROAKADEMIE_ENV_FILE")

if ENV_FILE:
    load_dotenv(
        ENV_FILE,
        override=False,
    )
else:
    # Lokální vývoj. Soubor .env je ignorovaný Gitem.
    load_dotenv(
        BASE_DIR / ".env",
        override=False,
    )
'''

base_dir_pattern = re.compile(
    r"BASE_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\.parent"
)

if 'ENV_FILE = os.getenv("ELEKTROAKADEMIE_ENV_FILE")' not in settings:
    match = base_dir_pattern.search(settings)
    if not match:
        raise SystemExit(
            "CHYBA: Nepodařilo se najít BASE_DIR v settings.py. "
            "Skript změny settings.py neuložil."
        )

    settings = (
        settings[:match.start()]
        + ENV_LOADER.rstrip()
        + settings[match.end():]
    )

secret_pattern = re.compile(
    r'(?m)^SECRET_KEY\s*=\s*(["\']).*?\1\s*$'
)

secret_replacement = '''SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Chybí povinná proměnná DJANGO_SECRET_KEY."
    )'''

if secret_pattern.search(settings):
    settings = secret_pattern.sub(
        secret_replacement,
        settings,
        count=1,
    )
elif 'SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")' not in settings:
    raise SystemExit(
        "CHYBA: SECRET_KEY v settings.py nemá očekávanou podobu. "
        "Skript změny settings.py neuložil."
    )

settings_path.write_text(settings, encoding="utf-8")

# 5) Lokální .env
if not env_path.exists():
    local_secret = secrets.token_urlsafe(64)

    LOCAL_ENV = f'''# Lokální konfigurace Elektroakademie.
# NIKDY NEPŘIDÁVAT DO GITU.

DJANGO_SECRET_KEY={local_secret}
DJANGO_DEBUG=True
SITE_URL=http://127.0.0.1:8000

# Dokud nechcete skutečně odesílat e-maily:
EMAIL_TRANSPORT=preview

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=
EMAIL_TIMEOUT=20
'''

    env_path.write_text(LOCAL_ENV, encoding="utf-8")
    print("Vytvořen nový lokální .env s novým náhodným DJANGO_SECRET_KEY.")
else:
    print("Existující .env nebyl přepsán.")

print()
print("HOTOVO:")
print("  requirements.txt         - python-dotenv")
print("  .gitignore               - ochrana .env")
print("  .env.example             - bezpečný veřejný vzor")
print("  config/settings.py       - načítání secrets z prostředí")
print("  .env                     - lokální tajná konfigurace")
print()
print("DŮLEŽITÉ:")
print("  Hodnotu DJANGO_SECRET_KEY ani EMAIL_HOST_PASSWORD nikdy necommitujte.")
print("  Produkční .env vytvořte na PythonAnywhere mimo Git repozitář.")
print()
print("Následující příkazy:")
print("  pip install -r requirements.txt")
print("  python manage.py check")
print("  python manage.py test courses")
