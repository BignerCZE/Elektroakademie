# Elektroakademie na PostgreSQL 17

Balíček patří na větev `main` s commitem `e2e9d5ef8bd271f718d28903d4169b06ecad95e2`. ZIP rozbalte do kořene projektu. Ověření používalo Python 3.13.5, Django 6.0.4, PostgreSQL 17.12 a Chromium 141 na Linuxu.

## Volba databáze

[Django 6.0](https://docs.djangoproject.com/en/6.0/ref/databases/) podporuje PostgreSQL 14+, MariaDB 10.6+ a MySQL 8.0.11+. Roští v dokumentaci ke sdíleným databázím služby Aplikace uvádí PostgreSQL 12 a MariaDB 10.4. Pro Django 6.0.4 jsou tyto verze pod podporovaným minimem. Služba [Roští Stacky](https://docs.rosti.cz/cs/stacks/apps-vs-stacks/) umožňuje provoz vlastního PostgreSQL kontejneru. Cílová verze je PostgreSQL 17 na Windows i ve Stacku. MariaDB v podporované verzi by také vyžadovala vlastní kontejner a další ověření chování zámků a přenosu dat.

- [Sdílené databáze Roští](https://docs.rosti.cz/cs/quickstart/databases/)
- [Příklad PostgreSQL ve Stacku](https://docs.rosti.cz/cs/stacks/quickstart/)

## Lokální čistá instalace

Spusťte Docker Desktop v režimu Linux containers. V PowerShellu v kořeni projektu spusťte následující příkazy. Hodnoty na úrovni procesu mají přednost před existujícím souborem `.env`.

```powershell
py -3.13 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r requirements.txt -r requirements-dev.txt
& $python -m playwright install chromium

$env:DJANGO_SECRET_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
$env:DJANGO_DEBUG = "True"
$env:SITE_URL = "http://127.0.0.1:8000"
$env:EMAIL_TRANSPORT = "preview"
$env:COMGATE_LIVE = "false"
$env:COMGATE_TEST = "false"
$env:COMGATE_CHECKOUT = "false"

$env:DB_ENGINE = "postgresql"
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "55432"
$env:POSTGRES_DB = "elektroakademie"
$env:POSTGRES_USER = "elektroakademie"
$env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString("N")
$env:POSTGRES_SSLMODE = "prefer"

docker compose -f compose.database.yml up -d --wait
& $python manage.py migrate --noinput
& $python manage.py check --database default
& $python manage.py makemigrations --check --dry-run
& $python manage.py test courses --noinput
& $python manage.py runserver 127.0.0.1:8000
```

Compose založí databázi a uživatele při první inicializaci svazku. Pro další relace použijte stejné databázové heslo a stejný lokální `DJANGO_SECRET_KEY`. Můžete si je uložit do místního ignorovaného `.env`. Pokud je načítá Docker Compose ze souboru `.env`, Django je načte ze stejného souboru. Změna hodnoty `POSTGRES_PASSWORD` u existujícího svazku nemění heslo databázové role. Při testech Django založí samostatnou databázi `test_elektroakademie`. Pro ruční proklik čisté instalace lze založit správce příkazem `& $python manage.py createsuperuser`. Obsah kurzů a otázek získáte importem nebo založením v administraci.

Následující příkazy spustí porovnatelný běh na SQLite v téže relaci.

```powershell
$env:DB_ENGINE = "sqlite"
& $python manage.py test courses --noinput
$env:DB_ENGINE = "postgresql"
```

## Přenos existující SQLite

Před přenosem zastavte zápisy do zdrojové aplikace. Vytvořte konzistentní kopii SQLite pomocí jeho zálohovacího rozhraní. Skript níže otevře původní soubor pouze pro čtení. Pro PG import použijte databázi po `migrate`, před založením správce či vložením jiných dat.

```powershell
New-Item -ItemType Directory -Force .\backup | Out-Null
$source = (Resolve-Path .\db.sqlite3).Path
$copy = Join-Path (Resolve-Path .\backup).Path ("sqlite-import-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".sqlite3")

@'
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

source, target = map(Path, sys.argv[1:])
target.touch(exist_ok=False)
with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
    with closing(sqlite3.connect(target)) as backup:
        original.backup(backup)
'@ | & $python - $source $copy
if ($LASTEXITCODE) { throw "Vytvoření kopie SQLite selhalo." }

$env:DB_ENGINE = "sqlite"
$env:SQLITE_PATH = $copy
& $python manage.py migrate --noinput
if ($LASTEXITCODE) { throw "Migrace kopie SQLite selhala." }

$env:DB_ENGINE = "postgresql"
& $python manage.py migrate --noinput
if ($LASTEXITCODE) { throw "Migrace PostgreSQL selhala." }
& $python manage.py import_sqlite $copy
if ($LASTEXITCODE) { throw "Import selhal." }
& $python manage.py check --database default
```

Příkaz vytvoří vlastní dočasný snímek a přenese data s původními primárními klíči. Zachovává uživatele včetně hashů hesel, členství a oprávnění, admin logy, objednávky, účastníky a profily, historické platby i Comgate, faktury včetně uložených PDF, obě číselné řady, otázky, pokusy, certifikáty a e-mailové záznamy. PostgreSQL ověří referenční integritu a příkaz porovná počty záznamů. Přesouvají se i záznamy relací. Platnost existujících přihlašovacích relací závisí mimo jiné na shodném `DJANGO_SECRET_KEY`. SQLite kopie patří mimo verzované soubory.

Na neveřejné PostgreSQL kopii zkontrolujte přihlášení existujícího účtu, vazby, stažení staré faktury i certifikátu, nové ID objednávky a další číslo faktury a účastníka. Novou zkušební fakturu vystavte na oddělené kopii, aby test neposunul účetní číselnou řadu v cílové databázi. Při přechodu ponechte zdrojovou SQLite jako zálohu. Pokud už PostgreSQL přijme nové zápisy, návrat na SQLite vyžaduje jejich vypořádání.

## Testovací Comgate

Automatické testy používají simulované odpovědi Comgate a e-mailové náhledy nebo testovací backend. Pro skutečný testovací checkout použijte testovací přihlašovací údaje a `COMGATE_TEST=true`, `COMGATE_LIVE=false`, `COMGATE_CHECKOUT=true`, `EMAIL_TRANSPORT=preview`. Hodnoty `COMGATE_MERCHANT_ID` a `COMGATE_SECRET` patří do privátní konfigurace. Automatický webhook vyžaduje veřejně dostupnou HTTPS adresu přidělenou testovacímu webu a uvedenou v Comgate. Pro lokální variantu bez veřejného webhooku nastavte `COMGATE_CHECKOUT=false`, založte objednávku § 4 a spusťte následující příkazy.

```powershell
& $python manage.py comgate_test create ID_OBJEDNAVKY
# Dokončete testovací platbu na URL vypsané příkazem.
& $python manage.py comgate_test status ID_OBJEDNAVKY TRANS_ID
& $python manage.py comgate_test apply ID_OBJEDNAVKY TRANS_ID
```

Ve Stacku spusťte PostgreSQL 17 s perzistentním uložením na interní síti, Django nasměrujte na interní jméno služby a ověřte migrace, obnovu zálohy, veřejnou HTTPS adresu a doručení testovacího webhooku. Automatické testy na hostingu spouštějte proti oddělené testovací databázi.

## Zjištění z ověření

- Původní náhled zasahoval do sloupce textu při šířkách 1201–1208 px při výšce 768 px, při 1280 × 768 a při 1201 × 480. Zavírací tlačítko původního přehrávače bylo částečně mimo okno například při 844 × 390. Po opravě prošla kontrola po jednotlivých pixelech kolem 420, 768, 900 a 1200 px a při krátkých, mobilních a notebookových rozměrech. Test ověřuje vložení iframe a zástupný obsah. Přehrávání u poskytovatele YouTube ověřte později v běžném prohlížeči.
- V Chromium obě nabídky § 6 a § 7 otevřely `/#contact`. Po vyplnění formuláře a kliknutí na Odeslat neodešel žádný požadavek. Aktuální formulář nemá obsluhu odeslání.
- Dva souběžné HTTP požadavky se stejným testovacím webhookem vedly k jedinému zpracování. Druhý požadavek dostal při běžícím zpracování HTTP 503, pozdější opakování dostalo HTTP 200. Vznikla jedna faktura a po jednom e-mailovém náhledu pro potvrzení a aktivaci. Test pokrývá aplikační souběh a retry. Pád procesu po přijetí zprávy SMTP serverem a před uložením stavu zůstává nejednoznačný a nebyl součástí tohoto testu.
- Přenos na PostgreSQL byl ověřen na syntetických záznamech včetně přihlášení, skupiny a oprávnění, vazeb, uloženého PDF a číslování. Další objednávka dostala ID 11 po dříve smazaném ID 10, další faktura končila číslem 0002 a evidenční číslo účastníka končilo 00003. Kontrolní součet zdrojového souboru zůstal shodný a opakovaný import do naplněného cíle skončil před změnou jeho dat.
- Testy běžely na Linuxu s PostgreSQL spuštěným přímo. Konfigurace prošla příkazem Docker Compose 2.39.4 `config --quiet`. Spuštění Docker Desktopu ve Windows, provoz na Roští a skutečný testovací požadavek z Comgate zbývá ověřit v cílovém prostředí.

| Běh | Výsledek |
|---|---|
| Výchozí GitHub `main`, SQLite | 351 z 353 prošlo. Dva testy čekaly starší verzi CSS a text o HlídáníRevizí.cz, který v šabloně už nebyl. |
| Upravená verze, SQLite | 355 z 355 prošlo, včetně 20 prohlížečových testů. |
| Upravená verze, PostgreSQL 17.12 | 355 z 355 prošlo, včetně 20 prohlížečových testů. Čisté migrace, systémová kontrola a kontrola chybějících migrací prošly. |

Úplné běhy ověřily individuální a skupinovou objednávku § 4, validaci a obnovu rozpracované objednávky, platební stavy, fakturu, aktivaci, přihlášení, dashboard, video, kvíz, certifikát, administraci a oprávnění. Samostatný proklik § 6 a § 7 potvrdil závadu při odeslání kontaktu uvedenou výše.
