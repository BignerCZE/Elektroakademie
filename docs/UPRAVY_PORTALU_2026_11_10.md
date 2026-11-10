# Elektroakademie – úpravy z 10. 11. 2026

Základ balíčku: větev `main`, commit `fa18bb3db6511d3b8cf7278a11da20ef84dc3e40` („Zobrazeni nahledu faktury primo jako PDF“). Repozitář byl nově stažen a jeho pracovní strom byl čistý. V repozitáři ani nadřazené pracovní složce nebyl nalezen AGENTS.md; dodané projektové instrukce byly respektovány. Balíček neobsahuje commit, push ani nasazení.

## Změny

### Kontrola dokončeného testu

V `courses/templates/courses/quiz_attempt_detail.html` je název kurzu v souhrnu nahrazen textem „Paragraf §4“. Jde o kontrolu již odevzdaného testu; formulář probíhajícího testu se nemění. Navigace používá názvy „Předchozí otázka“ a „Další otázka“, stejnou primární třídu a společné CSS. Na širokém zobrazení mají oba odkazy šířku 12 rem, do 768 px stejnou dostupnou šířku pod sebou. První otázka nemá předchozí odkaz, poslední nemá následující odkaz. Odkaz na přehled zůstává samostatný.

### Certifikát

Konkrétní text nad horní čárou byl v aktuálním kódu vykreslován řádkem `<p class="certificate-course">Kurz: {{ course.title }}</p>` ve sdílené šabloně `certificate_document.html`. Tento řádek je odstraněn. Logo, ostatní obsah i CSS podpisu s maximální výškou 22 mm zůstávají zachované. Sdílenou šablonu používá náhled, tisk i `generate_certificate_pdf`.

Přiložené ukázkové PDF obsahuje výhradně testovací údaje. Je skutečně vyrenderované z upravené projektové HTML šablony a jejího CSS, má 1 × A4 a bylo rasterizováno a vizuálně zkontrolováno včetně celé patičky a podpisu. **Bylo vytvořeno pomocí WeasyPrint 70.0, nikoli projektovým Chromiem.** Kvůli odlišnému rendereru se mohou drobnosti sazby lišit; například zobrazení značek seznamu. Nejde o potvrzení shodného výsledku produkčního PDF rendereru. WeasyPrint se do aplikace ani jejích závislostí nezavádí.

### Návrat po aktivaci

Uživatel potvrdil, že jde o šipku Zpět v prohlížeči. Po úspěšném POST a přesměrování na dashboard zůstává aktivační stránka v historii. Prohlížeč ji může obnovit z paměti bez nové kontroly tokenu. Původní větev pro použitý token navíc vykreslovala samostatnou stránku místo návratu domů.

Aktivační endpoint nyní používá `never_cache`. Při obnovení stránky z historie nebo BFCache malý samostatný skript znovu otevře stejnou URL pomocí `location.replace`, aby server ověřil aktuální stav tokenu. Již aktivovaný účastník přihlášený ke svému účtu je přesměrován na domovskou stránku. Cizí či nepřihlášená relace stále dostane informaci o použitém odkazu. Úspěšná aktivace nadále přihlašuje a směruje na dashboard. Do obecné historie dashboardu se nevkládají žádné umělé položky.

Serverové chování je otestováno. Skutečné obnovení historie/BFCache v prohlížeči zde nebylo možné ověřit; je nutné spustit přiloženou browser regresi nebo níže uvedenou ruční kontrolu.

### Platby a faktury

Starý `Payment` obsahuje vazbu na jednotlivého uživatele a kurz. Aktuální skupinové objednávky používají `Order` a vystavené faktury `Invoice`, která má vazbu 1:1 na objednávku. Propojení starého Payment s objednávkou v modelu neexistuje a současné platební workflow tyto záznamy nevytváří. Jejich párování podle uživatele by bylo zavádějící.

Nová sekce „Platby a faktury“ proto používá **proxy model nad existujícími objednávkami**. Nevznikají nové platby, duplicitní objednávky, faktury ani účetní tabulka. Zobrazuje i objednávky bez vystaveného dokladu se stavem „Faktura nevystavena“, bez PDF odkazů. Starý seznam byl přejmenován na „Historické platby (původní workflow)“ a zůstává přístupný jen s původními právy. Existující sekce „Faktury“ zůstává detailním pohledem na stejné doklady; její PDF odkaz také používá nový chráněný endpoint.

Sloupce čísla a data čtou přímo `Invoice.number` a `Invoice.issued_on`. Vyhledávání podporuje číslo faktury i firmu. Náhled otevírá PDF v nové kartě (`inline`), samostatné stažení používá `attachment`. Oba vracejí výhradně uložené `pdf_content`; nevystavují doklad, nečerpají řadu ani nepřegenerovávají PDF. Pokud doklad existuje, ale uložené PDF chybí, endpoint vrátí srozumitelnou zprávu 503; nápravu je třeba provést původním platebním workflow, nikoli otevřením dokumentu.

Sekce vyžaduje explicitní `courses.view_invoice`. Samotné `is_staff`, `view_order`, `view_payment` ani právo upravovat jiný model přístup neudělují. Právo přidělí superuser účtu nebo skupině přes standardní administraci. Nové proxy modelové oprávnění se nevytváří. Přímá URL `/sprava/faktury/<order_id>/pdf/` a varianta `?download=1` kontrolují aktivní staff účet i `view_invoice`; nepoužívají případné veřejné oprávnění objednávkové relace. Původní objednávkové PDF URL pro vlastní objednávku zůstává zachováno.

`select_related("invoice")` načte vazbu jedním dotazem; velké PDF a snapshot jsou v seznamu odložené. Test ověřuje jediný dotaz při vykreslení nových sloupců několika řádků.

Formát YY30NNNN, roční čítač Europe/Prague, uložené snapshoty a PDF, nečíslovaný náhled před platbou i fakturační logo zůstávají beze změny. SMTP ani skutečná brána nebyly zapojeny. Veškeré ověřování používalo EMAIL_TRANSPORT=preview.

## Ověření a omezení

- Pomocné prostředí: Python 3.13.5, Django 6.0.4. Projektové requirements se nemění; nejde o identický patch Pythonu 3.13.1 uživatele.
- Finální cílená sada: **31/31 OK** (aktivace včetně objednávka → simulovaná platba → aktivace → dashboard → návrat na aktivační URL, fakturační administrace a oprávnění, stálost uložených PDF, první/střední/poslední otázka a certifikát).
- Širší sada: **301 testů, OK, 4 přeskočené**; 297 provedených testů prošlo. Tato sada běžela v dočasném testovacím harnessu s HTML→PDF funkcí nahrazenou WeasyPrintem. Čtyři přeskočené testy potřebují dostupný Playwright Chromium (dvě původní browser regrese a dvě nové). Po této sadě přibyl ještě serverový test celého průchodu, který je zahrnut v uvedených 31 finálních cílených testech. Nejde o plné potvrzení produkčního Chromium rendereru.
- Standardní kompletní sada s projektovým rendererem zde nemůže úspěšně doběhnout: systémový Chromium selhává na `socket() failed: Operation not permitted`; stažení Playwright Chromia vracelo poškozený archiv. Místní HTML náhled v desktopovém prohlížeči byl navíc blokovaný pravidly prostředí. Tyto limity nebyly obcházeny.
- `manage.py check`, `makemigrations --check --dry-run`, syntaxe nového JS a `git diff --check`: OK.
- Testy skutečného browser Zpět/BFCache a rozměrů tlačítek při 1366/390/320 px jsou přiložené v `test_portal_navigation_browser.py`, zde však nebyly provedeny. Objednávku v tomto testu založí skutečný serverový POST, simulovanou platbu spustí skutečný odpočet a aktivace probíhá přes formulář; pouze generování přílohy faktury je v této navigační regresi stubované.

## Použití lokálně

ZIP obsahuje pouze změněné a nové soubory, s cestami od kořene projektu. Před rozbalením zálohujte databázi a vlastní rozpracované soubory. Pokud máte novější změny než výchozí commit, nejdříve porovnejte rozdíly; ZIP obsahuje celé soubory.

Ve svém aktivovaném virtuálním prostředí spusťte v PowerShellu z kořene projektu:

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test courses.tests.test_activation courses.tests.test_billing_overview courses.tests.test_certificate_document courses.tests.test_quiz_review
python -m playwright install chromium
python manage.py test courses.tests.test_portal_navigation_browser
python manage.py test courses
python manage.py runserver
```

Ponechte svůj existující DJANGO_SECRET_KEY v `.env`. Nové závislosti nejsou pro aplikaci potřeba. Pokud již máte kompatibilní Chromium, jeho instalaci neopakujte. Pro systémový Chromium lze nastavit CHROMIUM_EXECUTABLE_PATH na jeho skutečnou cestu; jinak proměnnou nechte nenastavenou a použije se Playwright browser.

**Migrace 0021 je nutná.** Přidává pouze stav proxy modelu a mění zobrazovaný název historických plateb. Nevytváří účetní záznamy ani nové datové tabulky a nepřečísluje faktury. Původní migrace 0020 zůstává beze změny.

## Ruční ověření

1. Na počítači i mobilu otevřete dokončený test: první otázka pouze „Další otázka“, prostřední obě stejně velká a barevná tlačítka, poslední pouze „Předchozí otázka“. Zkontrolujte štítek „Paragraf §4“. Probíhající test musí zůstat funkční.
2. Dokončete novou testovací objednávku, vyčkejte simulovanou platbu, otevřete aktivaci, odešlete formulář a ověřte dashboard a přístup k videu. Stiskněte šipku Zpět v prohlížeči: výsledkem má být domovská stránka. Ověřte také BFCache v používaném prohlížeči, opětovné otevření odkazu v přihlášené relaci a v anonymním okně; nesmí vzniknout druhý účet.
3. Staff účet bez práv nesmí vidět „Platby a faktury“ ani „Faktury“ a přímé administrativní PDF URL musí vracet 404. Superuser přidělí `courses.view_invoice`; poté se zpřístupní nový přehled a oba PDF odkazy.
4. Vyhledejte skutečné číslo faktury. Ověřte datum vystaveného dokladu, náhled v nové kartě a samostatné stažení do souboru. Otevřete dokument opakovaně: číslo a obsah musí zůstat stejné. Objednávka bez faktury musí mít srozumitelný stav a žádné PDF odkazy. Pouhá návštěva administrace ani PDF nesmí fakturu vystavit.
5. Vytvořte testovací úspěšný pokus, otevřete náhled certifikátu, tisk a stáhněte PDF přes skutečný projektový renderer. Ověřte odstraněný řádek, zachované logo, podpis 22 mm a jednu A4. Toto lokální ověření Chromia je před přijetím změn stále potřeba.

## Pozdější PythonAnywhere

V této dodávce se nenasazuje. Až po samostatném pokynu, commitu a pushi použijte:

```bash
bash ~/update_elektroakademie.sh
```

Aktualizace musí zahrnout migraci 0021, collectstatic a reload. Databázi ani existující faktury kvůli této změně nemažte.
