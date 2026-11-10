# Spuštěný test v popupu a centrování všech oken

Balíček navazuje na poslední sjednocený přehled, bílé kontejnery, tři kroky a opravu odchodu z testu. Obsahuje 13 nových a změněných souborů včetně této dokumentace. Rozbalte do kořene projektu se zachováním struktury; vlastní novější změny nejprve porovnejte.

## Chování

- Spustit test, Spustit nový test i Pokračovat v testu v přehledu otevírají test v popupu stejného vzhledu jako historie. Přehled zůstává na pozadí.
- Test běží v samostatném rámci ze stejného webu. Používá původní formuláře, přihlášení, CSRF, ukládání odpovědí, navigaci, kontrolu všech odpovědí před odesláním a původní dokončovací workflow.
- Záložka/rámec neobsahuje druhé logo, menu ani patičku. Nové spuštění zůstává POST požadavkem; pokračování používá původní existující pokus.
- Opustit test v hlavičce, Escape nebo kliknutí na pozadí nabídnou potvrzení. Při potvrzení se odešle aktuální odpověď přes původní serverovou cestu leave_test. Přehled se obnoví a nabídne pokračování. Také původní Zpět na první otázce zachovává toto chování.
- Po odeslání se obnoví přehled a automaticky otevře kontrola dokončeného pokusu v existujícím popupu historie. Pokud prohlížeč nepovoluje sessionStorage, přehled se obnoví, ale kontrolu bude třeba otevřít ručně.
- Historie, odpovědi, certifikát, video i aktivní test mají výslovné `position: fixed; inset: 0; margin: auto`. Globální CSS reset jim dříve přepisoval okraje, což způsobovalo umístění vlevo nahoře. Okna videa a certifikátu mají výšku podle obsahu; historie a test si zachovávají omezení na výšku viewportu.

## Technické hranice

Režim `?popup=1` podporují pouze existující endpointy spuštění, otázky a odeslání testu. Pomocný dekorátor zachovává režim při přesměrování mezi otázkami a při odchodu/dokončení vrací minimální oznamovací stránku. V tomto režimu jsou odpovědi `private, no-store` a `X-Frame-Options: SAMEORIGIN`; nezpřístupňují se rámcům z cizích webů.

Rodič přijímá oznámení jen ze svého konkrétního iframe a stejného originu. Kontroly vlastníka pokusu, jednorázového odeslání a souběhu zůstávají v původním backendu. Bez JavaScriptu zůstává dostupný dosavadní samostatný průchod. Nezměnily se faktury, číslování ani oprávnění; SMTP ani skutečná brána nebyly zapojeny.

## Ověření

- 39 cílených serverových testů prošlo: spuštění a pokračování v popup režimu, přenos režimu mezi otázkami, uložení odpovědi při odchodu, zachování rozpracovaného pokusu, dokončení, vlastnictví, původní kvíz i přehled a historie.
- Django check, makemigrations --check --dry-run, syntaxe obou JS a git diff --check: OK.
- Čtyři browser testy byly zde přeskočené kvůli chybějícímu Playwright Chromiu. Browser regrese byla rozšířena o geometrické centrování popupu a průchod aktivní test → uložení/odchod → pokračování → odeslání → kontrola odpovědí. Skutečný výsledek v prohlížeči je nutné ověřit lokálně.
- Nové migrace ani závislosti nejsou potřeba. CSS a JS pro přehled mají verzi 4 pro obnovu cache.

## Lokální postup

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py test courses.tests.test_quiz_active_popup courses.tests.test_portal_overview_browser
python manage.py test courses
python manage.py runserver
```

Po Ctrl+F5 v přehledu vyzkoušejte nové spuštění i pokračování. Ověřte první/poslední otázku, navigaci podle čísel, uložení při opuštění, zrušení odchodu a dokončení. Vše má zůstávat v popupu a po dokončení se má aktualizovat stav přehledu. Zkontrolujte střed obrazovky u historie, odpovědí, videa a certifikátu na počítači i telefonu.

Commit, push ani nasazení nebyly provedeny.
