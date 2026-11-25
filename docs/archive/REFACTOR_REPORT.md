# Elektroakademie – frontendový refaktor

## Výchozí stav

- Zdroj: větev `main`, commit `ae86334aabdedca94c161309d7a469d16eb9b212` (`Uprava kontaktni a FAQ sekce uvodni stranky`).
- Pracovní strom byl před zahájením čistý.
- Audit zahrnul 43 HTML/Django šablon, stávající statické soubory, odkazy přes `{% static %}`, Django hodnoty a URL uvnitř JavaScriptu, formuláře, CSRF, `fetch`, navigaci, modaly, FAQ scroll a související testy.

## Původní inline bloky

Nalezeno bylo 6 inline `<style>` bloků:

1. `courses/templates/courses/index.html` – FAQ scroll fix; přesunuto na konec `courses/static/courses/css/landing.css`.
2. `courses/templates/registration/register.html` – styly registrace a ARES; přesunuto do `courses/static/courses/css/registration.css`.
3. `courses/templates/courses/certificate_print.html` – styly tiskového náhledu; přesunuto do `courses/static/courses/css/certificate-print.css`.
4. `courses/templates/courses/certificate_pdf.html` – ponecháno inline kvůli samostatnému PDF renderování.
5. `courses/templates/courses/certificate_pdf_browser.html` – ponecháno inline kvůli samostatnému dokumentu používanému při generování PDF.
6. `courses/templates/emails/base.html` – ponecháno inline kvůli kompatibilitě HTML e-mailů.

Nalezeno bylo 9 inline `<script>` bloků:

1. `courses/templates/courses/base.html` → `courses/static/courses/js/base.js`.
2. `courses/templates/courses/index.html` → `courses/static/courses/js/landing.js`.
3. `courses/templates/registration/register.html` → `courses/static/courses/js/registration.js`.
4. `courses/templates/courses/quiz_question.html` → `courses/static/courses/js/quiz-question.js`.
5. `courses/templates/courses/certificate_success.html` → `courses/static/courses/js/certificate-preview.js`.
6. `courses/templates/registration/payment_simulation.html` → `courses/static/courses/js/payment-simulation.js`.
7. `courses/templates/registration/order_payment_success.html` → `courses/static/courses/js/payment-success.js`.
8. `courses/templates/registration/register_5step_summary.html` – ponecháno beze změny; jde o osiřelý legacy fragment, na který neodkazuje žádný view ani jiná šablona a sám nemá dokument ani blok pro bezpečné načtení statického souboru.
9. `courses/templates/registration/register_validated_5step.html` – ponecháno beze změny; jde o nepoužívanou legacy variantu, na kterou neodkazuje žádný view ani URL konfigurace.

V aktivních aplikačních šablonách po refaktoru nezůstává žádný inline `<style>` ani inline `<script>` blok. Nebyly nalezeny atributové JavaScript handlery jako `onclick`.

## Řešení dynamických hodnot

Statické JS soubory neobsahují Django template tagy.

- Registrační URL `check_participant_emails` a `index` se renderují jako `data-check-emails-url` a `data-index-url` na formuláři.
- URL výsledku simulované platby se renderuje jako `data-success-url` na elementu stránky.
- URL úvodní stránky po dokončení platby se renderuje jako `data-index-url`.
- CSRF token zůstává v HTML formuláři a `registration.js` jej nadále čte ze stejného hidden inputu.
- ARES endpoint zůstává relativní URL sestavenou z bezpečně kódovaného IČO.

Pořadí inicializace je zachováno pomocí `defer` a existujících listenerů `DOMContentLoaded`. FAQ wheel listener si zachoval `{ passive: false }`, `preventDefault()`, interní scroll i přechod z horní hranice na Kontakt.

## Změněné a nové soubory

Úplný strojově čitelný seznam je v `CHANGED_FILES.txt`.

## Kontroly

- Ověření Git výchozího stavu: OK.
- Django template syntax: OK, zkompilováno 43 šablon.
- JavaScript syntax: OK, všechny nové `.js` soubory prošly `node --check`.
- CSS závorky: OK pro všechny CSS soubory projektu.
- Django tagy ve statických CSS/JS: nenalezeny.
- `git diff --check`: OK.
- Nové chybějící statické odkazy: žádné.
- Inline audit po refaktoru: 3 záměrně ponechané CSS bloky a 2 nepoužívané legacy JS bloky popsané výše.
- `python manage.py check`: nebylo možné dokončit, protože pracovní runtime neobsahoval všechny balíčky z `requirements.txt` a síť instalaci závislostí nedovolila dokončit.
- `python manage.py test courses`: ze stejného důvodu nebylo možné spustit kompletní sadu. Přidané testy jsou připravené v `courses/tests/test_frontend_static_assets.py`.

Při kontrole statických odkazů byla nalezena starší chyba už ve výchozím commitu: `courses/templates/courses/certificate_document.html` odkazuje na neexistující `courses/images/signature_jakub_jirak.png`. Refaktor tento odkaz neměnil. Před nasazením je vhodné ověřit, zda soubor existuje pouze lokálně/produkčně, nebo jej doplnit do repozitáře samostatně.

## Opakování kontrol

```powershell
python manage.py check
$env:EMAIL_TRANSPORT = "preview"
python manage.py test courses

Get-ChildItem courses/static/courses/js/*.js | ForEach-Object {
    node --check $_.FullName
}

git diff --check
git status
```

## Vizuální checklist

Kontrolu proveďte v rozlišeních 1920 × 1080, 1366 × 768, tablet kolem 768 px a mobil 375–430 px.

### Úvodní stránka

- Logo, desktopová i mobilní navigace a aktivní položka navigace.
- Přechody Úvod, Školení, FAQ a Kontakt.
- Programové taby, obsah jednotlivých panelů a odkazy do panelů.
- Otevření a zavření video modalu tlačítkem, backdropem a klávesou Escape.
- Správný výpočet výšky hlavičky po načtení a změně velikosti okna.
- Aktuální Kontakt včetně předmětů a firemních údajů.
- Pevný nadpis „Často kladené otázky“.
- Interní scroll seznamu FAQ, bez rolování nadpisu.
- Wheel scroll na horní hranici FAQ přejde zpět na Kontakt.
- Mobilní jednosloupcové FAQ a responzivní odsazení.

### Registrace a aktivace

- Všechny kroky registrace, návrat mezi kroky a obnovení konceptu.
- Volba kurzu, účastníci, ruční přidávání/odebírání a ceny.
- ARES načtení, chybové stavy a ruční fakturační údaje.
- Kontrola duplicitních e-mailů a CSRF POST.
- Validace povinných polí a červené zvýraznění chyb.
- Obchodní podmínky a privacy modal.
- Simulace platby, countdown, redirect a kopírování aktivačních odkazů.
- Aktivace účastníka včetně polí Den/Měsíc/Rok, ručního vstupu i seznamů.

### Přihlášení a kurz

- Přihlášení, odhlášení a mobilní menu.
- Dashboard, profil, detail kurzu a stav sidebaru.
- Přehrávání videa.
- Test: výběr odpovědi, navigace, opuštění, nevyplněné otázky a odeslání.
- Certifikát: otevření/zavření modalu, tiskový náhled a PDF.

### E-maily a administrace

- Náhled aktivačního, platebního a dokončovacího e-mailu.
- Admin objednávek, účastníků, testových pokusů a certifikátů.
- Detailní admin styly, odkazy na náhledy a exporty.

## Doporučený overlay postup

1. Ověřit čistý nebo vědomě rozpracovaný pracovní strom.
2. Vytvořit záložní větev nebo kontrolní commit vlastních změn.
3. Rozbalit obsah adresáře `Elektroakademie_frontend_refaktor` do kořene projektu a povolit nahrazení souborů.
4. Spustit kontrolní příkazy a celý vizuální checklist.
5. Zkontrolovat diff; teprve poté commitnout.

## Doporučený commit message

```text
Refaktor frontendovych CSS a JavaScript souboru
```
