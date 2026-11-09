# Roční číslování faktur a logo bez sloganu

Stav připravených změn k 9. 11. 2026. Zdrojový repozitář: main / ba940e2de5a0f48a410f4fe970f13273b35d7d9d. Tento balíček navazuje na předchozí fakturační balíček a obsahuje i jeho soubory, protože na GitHubu dosud nejsou.

## Co je upraveno

- Nové faktury mají číslo YYNNNNN: 2600001, 2600002, …, 2699999. Každý rok začíná od 00001, měsíc pořadí nemění. Rok se počítá podle Europe/Prague.
- Číslování zůstává chráněné transakcí a zápisovým zámkem SQLite, databázovou unikátností čísla, vazbou 1:1 na objednávku a unikátní dvojicí období/pořadí.
- Již vystavené měsíční faktury se nepřečíslují. Starší období 202611 mohou zůstat vedle nového ročního období 2026. Úspěšně uložená PDF a snapshoty zůstávají beze změny. Proto zůstala maximální délka databázového čísla 9 a období 6; nové hodnoty jsou kratší. Není potřeba měnit schéma ani existující migrační soubor 0020.
- Nové faktury používají logo courses/static/courses/img/svetle_pozadi_bez_sloganu.svg. Odkaz je změněn také v HTML náhledu certifikátu i v jeho PDF rendereru. Logo na ostatních stránkách se nemění.
- Starší vystavené faktury si zachovávají své uložené logo a PDF. U certifikátů se nová varianta loga projeví při jejich dalším zobrazení nebo generování.

## Co chybí pro dokončení

Soubor svetle_pozadi_bez_sloganu.svg nebyl v dostupném GitHubu ani přílohách této konverzace nalezen. Balíček jej neobsahuje ani nenahrazuje odhadovaným obrázkem. Před spuštěním musíte mít svůj skutečný soubor na cestě:

    courses/static/courses/img/svetle_pozadi_bez_sloganu.svg

Bez něj nelze finálně zkontrolovat vzhled a generování nových dokumentů skončí chybou chybějícího statického souboru. Pomocný testovací obrázek použitý při kontrole není součástí balíčku ani produkčního kódu. Tento stav není považován za nasazení.

## Použití v lokálním projektu

Zálohujte databázi a zkontrolujte vlastní rozpracované změny. ZIP obsahuje celé změněné soubory pro uvedený základ; nepřepisujte jím vlastní pozdější úpravy naslepo. Rozbalte do kořene Elektroakademie a zachovejte adresářovou strukturu. Doplňte skutečné SVG a ve virtuálním prostředí spusťte v PowerShellu:

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py findstatic courses/img/svetle_pozadi_bez_sloganu.svg
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test courses
python manage.py runserver
```

Findstatic musí ukázat skutečnou cestu k dodanému souboru. Je-li fakturační migrace 0020 už aplikovaná, migrate nic nového neprovede; pokud předchozí balíček ještě nainstalován není, vytvoří fakturační tabulky. Žádná migrace pro roční řadu není nutná.

Ověřte novou testovací objednávku, náhled faktury na simulované platbě, vystavené PDF a náhled i PDF certifikátu. Dřívější faktury ani číselné řady nemažte kvůli změně loga. Stávající náhledový režim e-mailů zůstává zachovaný.

## Pozdější PythonAnywhere

Přímé nasazení, commit ani push v této dodávce neproběhly. Po doplnění SVG, ověření a přenesení změn včetně SVG na GitHub použijte svůj zavedený příkaz:

```bash
bash ~/update_elektroakademie.sh
```

Skript musí provést migrate, collectstatic a reload. Bez přenesení změn na GitHub tento příkaz sám připravené soubory nezíská. Není připojena skutečná platební brána a nebyly odeslány skutečné e-maily.

## Provedené kontroly

- Celá Django sada: 289/289 OK (62,352 s), Python 3.13.17 / Django 6.0.4, Playwright 1.55.0 / Chromium 140.
- V této kontrole bylo pouze chybějící nové logo nahrazeno pomocným SVG v externím testovacím launcheru. Náhrada není v aplikaci ani v ZIPu. Výsledky ověřují roční číslování, souběh, opakování, zachování starých dokladů, oprávnění, ceny a PDF mechanismus; nepotvrzují vzhled skutečného nového loga.
- Nové regresní kontroly ověřují přechod listopad → prosinec bez resetu, leden s resetem v pražském čase, uchování starého měsíčního čísla a PDF, oddělení staré a nové číselné řady a použití nové cesty v rendereru certifikátu.
- Django check, makemigrations --check --dry-run a git diff --check: OK.
