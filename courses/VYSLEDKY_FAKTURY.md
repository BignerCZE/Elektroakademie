# Historické výsledky ověření faktur ze 4. 11. 2026

Tento report popisuje předchozí dodávku s měsíční řadou a původním logem. Aktuální změnu z 9. 11. 2026 a omezení kontroly chybějícího SVG popisuje docs/LOGO_A_ROCNI_FAKTURY_2026_11_09.md.

Datum: 4. 11. 2026. Základ: main / ba940e2de5a0f48a410f4fe970f13273b35d7d9d.
Při zahájení čistý pracovní strom; repozitář byl čerstvě stažen z GitHubu. V repozitáři nebyl soubor AGENTS.md; byly respektovány instrukce uživatele. Projektové dokumenty a současné modely, objednávky, platby, oprávnění, e-mailové workflow a oba existující PDF mechanismy byly prostudovány.

## Automatické kontroly

- Celá Django sada: 287/287 OK, 67,835 s, bez vynechaných testů.
- Z toho 18 nových fakturačních testů. Cílená sada faktury + frontend static assets: 28/28 OK.
- Souběžný běh 8 vláken: stejné objednávce vždy stejné číslo, různé objednávky s unikátními navazujícími čísly. Ověřeno jak na testovací shared-cache SQLite, tak samostatně na souborové SQLite (1/1 test OK).
- Měsíční a roční přechod včetně UTC okamžiku odpovídajícího půlnoci v Praze, vyčerpání měsíční řady, databázové unikátní vazby: OK.
- Serverové ceny, podvržené ceny z prohlížeče, starší objednávky bez uložených položek, nesoulad cen: OK.
- Zachování vystaveného obsahu po změně firmy, cen i účastníků: OK.
- Vlastní relace, cizí objednávka, anonymní přístup, staff bez práv, explicitní práva správce: OK.
- Selhání PDF, neplatný výstup, HTTP 503 a bezpečné opakování, trvalé uchování PDF: OK.
- Selhání e-mailu a opakování; čekání platebního potvrzení na úspěšnou přílohu: OK.
- JavaScript cookies: 13/13 OK.
- Django check, makemigrations --check --dry-run, node --check změněného skriptu a git diff --check: OK.
- Migrace 0020 byla skutečně aplikována na místní testovací databázi.

## Prohlížeč a PDF

- Playwright: náhled na simulaci nemá přidělené číslo, úvodní odpočet je 30, po 29 sekundách zbývá 1, po 30 sekundách proběhne přesměrování a PDF je přístupné oprávněné relaci.
- Skutečně vytvořené jednostránkové PDF pro 2 účastníky / 1 980 Kč a čtyřstránkové PDF pro 30 položek / 29 700 Kč.
- Všechny stránky poslední verze byly vizuálně prohlédnuty po rasterizaci. Česká diakritika, vložené logo a písmo, dlouhé fakturační údaje, opakované záhlaví tabulky, patičky s číslem faktury a stránkování i závěrečné součty jsou čitelné a bez překryvů.
- Vzhled vychází z dodaného XLSX: dva bloky dodavatel/odběratel, bankovní a identifikační údaje, termíny, položková tabulka, DPH a informace o zaplacení. Logo používá stávající projektové SVG pro bílé pozadí. Velká prázdná oblast tabulky ze sešitu nebyla přenesena do PDF.

## Prostředí a rozsah

Pomocné prostředí: Python 3.13.17, Django 6.0.4, ReportLab 4.4.10, Playwright 1.55.0 / Chromium 140.0.7339.16. Verze Pythonu je novější patch než uživatelova 3.13.1. Pomocné PDF knihovny zahrnují pypdf 6.21.4 a xhtml2pdf 0.2.28; projektový requirements.txt zůstává nezměněn. Nová faktura používá stávající Chromium renderer, nikoli nový balíček.

Skutečné e-maily nebyly odesílány a platební brána nebyla připojena. Všechny průchody běžely s EMAIL_TRANSPORT=preview, transportní testy používají mock/locmem mechanismy. Poslední opravy testů, právních textů, oprávnění a účastníků zůstaly zachované; jejich regrese je součástí celé sady.

Commit, push ani nasazení nebyly provedeny. Podrobný postup použití a nasazení: docs/FAKTURY_2026_11_04.md.
