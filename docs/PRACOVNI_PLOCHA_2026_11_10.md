# Nové rozložení uživatelské části

Navazuje na poslední balíček s historií a prohlížením odpovědí ve společném popupu (`elektroakademie_popup_testu_2026_11_10.zip`). ZIP obsahuje sedm změněných a nových souborů včetně této dokumentace. Rozbalte jej do kořene projektu se zachováním struktury. Případné vlastní novější úpravy dotčených souborů nejprve porovnejte.

## Vzhled

- Zrušen levý sloupec v uživatelské části. Nahradil ho úzký řádek účtu se jménem a účastnickým kódem vlevo, odkazy Mé údaje a odhlášením vpravo. E-mail a ostatní osobní údaje zůstávají na stránce Mé údaje.
- Na dalších stránkách uživatelské části obsahuje řádek také odkaz Přehled kurzu, aby byl možný návrat z údajů či samostatných detailů.
- Logo zůstává nahoře uprostřed. Odhlášení je stále POST s CSRF a návratem na homepage.
- Přehled nemá vnější bílou kartu, uvítání ani obecný popis kurzu. Vlevo je nadpis Paragraf §4 a větší náhled videa přímo na modrém pozadí, vpravo jediný světlý panel Závěrečný test s certifikátem pod dělicí čárou.
- Hlavní akce testu je zelená; ovládání certifikátu je klidnější, s modrým stažením PDF. Méně vnořených rámečků a menší zaoblení odlišují hlavní stránku od popupů.
- Na telefonu se řádek účtu zalomí a video i test se seřadí pod sebe. Všechen obsah zůstává dosažitelný i při menší výšce okna či zvětšeném písmu.

## Zachované funkce a popupy

Markup všech popupů, soubor portal-overview.css a portal-overview.js byly porovnány s posledním předaným balíčkem a jsou beze změny. Nový vzhled hlavní plochy je v samostatném souboru portal-workspace.css a jeho selektory jsou omezené na přehled za popupy. Otevření videa, cookie souhlas, historie, prohlížení otázek ve společném okně, návrat na seznam i náhled certifikátu zůstávají zachované.

Nedošlo ke změně backendu, oprávnění, testovacího workflow, certifikátů, faktur ani číslování. Veřejná homepage se nemění. SMTP ani platební brána se nezapojují. Commit, push ani nasazení nebyly provedeny.

## Ověření

- Cílená sada: 45/45 OK (přehled, návrat z osobních údajů, popup fragmenty, kontrola dokončeného testu, přístupy a aktivace).
- Django check, makemigrations --check --dry-run a git diff --check: OK.
- Tři browser testy zde byly přeskočené kvůli chybějícímu Playwright Chromiu. Skutečná vizuální podoba v prohlížeči, rozměry a průchod popupy musí být ověřeny lokálně. Existující browser regrese nadále zahrnuje rozlišení 1920×1080, 1440×900 a 1366×768, mobilní šířky, historii, odpovědi, certifikát a odhlášení; přibyla kontrola horního účtového řádku a absence sidebaru.
- Nová databázová migrace ani závislost není potřeba.

## Použití a kontrola

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py test courses.tests.test_portal_overview courses.tests.test_portal_overview_browser
python manage.py runserver
```

Po otevření přehledu proveďte Ctrl+F5. Ověřte nové rozložení na počítači i telefonu, přechod do Mé údaje a zpět na Přehled kurzu, odhlášení a všechny stávající popupy. Nejde o nové schvalování jejich vzhledu; ten má zůstat zachovaný.
