# Validace objednávky – 11. 11. 2026

## Výchozí stav a rozsah

Nově stažený https://github.com/BignerCZE/Elektroakademie, větev `main`, commit `4c1bd8a` (`Odstraneni nahledu faktury a pridani preskoceni simulovane platby`), původně čistý pracovní strom. V repozitáři ani nadřazené pracovní složce nebyl nalezen AGENTS.md. Respektovány byly instrukce dodané v zadání. Prostudovány byly aktivní šablona, JS, CSS, formuláře, formset, modely, views, URL/dekorátor kurzů, ARES, sdílené úložiště konceptu, testy a projektová dokumentace k prostředí, refaktoru a posledním úpravám.

Přítomnost poslední platební změny byla ověřena: náhled faktury v simulaci není, odkaz „Přeskočit odpočet a pokračovat“ vede na stejný výsledek platby jako automatický přechod po 30 sekundách. Platební soubory, faktury, číslování ani aktivace se touto opravou nemění. Bez commitu, pushe a nasazení. Všechny provedené běhy používaly `EMAIL_TRANSPORT=preview`, žádné SMTP ani skutečná platební brána.

## Příčina a reprodukce

Původní hodnoty z uživatelova pokusu nejsou známé. Nelze tvrdit, kterou z nich skutečně zadal. Ve výchozím kódu však byly nalezeny a reprodukovány dva samostatné mechanismy odpovídající popisu:

1. V kroku účastníků se ověřovala pouze neprázdnost jména, příjmení a e-mailu. Kontrola dostupnosti e-mailů ověřovala účty a duplicity, nikoli syntaxi. E-mail `broken` tak prošel do kroku 4 a následně do shrnutí. Formulář neměl `novalidate`; při finálním kliknutí nativní validace HTML zjistila chybu v `input type=email` ve skrytém panelu 3. Událost `submit` se vůbec nevyvolala, JS handler ji tedy nemohl vysvětlit a server nedostal finální POST. Fokus na takové pole vyžaduje nejprve odkrytí panelu. Konkrétní konzolový text „invalid form control is not focusable“ zde nebyl ve skutečném Chromiu pozorován, protože prohlížeč nešel spustit.
2. Hodnota `jan@firma` může projít HTML email validitou, ale ne Django EmailValidator. Telefon `letters` prošel kontrolou neprázdnosti i nativní HTML validitou (textové pole bez číselného patternu), ale odmítl jej `BillingForm.clean_contact_phone`. Finální POST vracel chyby, zatímco inicializace stránky mohla obnovit starý localStorage koncept přes hodnoty odmítnutého POSTu. `selected_course` se navíc při vrácení stránky renderoval prázdný. To zhoršovalo návrat ke správnému kroku a zachování hodnot.

**Provedená reprodukce:** skutečný nezměněný commit byl spuštěn s Django serverem a jeho skutečné HTML a JS v jsdom. První případ skončil v panelu 5, chybný e-mail byl skrytý, `form.checkValidity()` byl false, počet událostí `submit` byl 0 a jediný síťový požadavek JS byla kontrola dostupnosti e-mailů. Ve druhém případě byla nativní validita true a skutečný POST na původní Django vracel HTTP 200 s chybou e-mailu i telefonu. Jde o **DOM simulaci a reálné serverové požadavky, nikoli skutečný browser průchod**.

Lokální reprodukce před opravou: vybrat §4 → účastník Jan/Test/`broken` → vyplnit jinak platnou fakturaci → shrnutí → souhlas → dokončit. Druhá varianta: `jan@firma` nebo telefon `letters`. Po opravě se příslušný údaj odmítne už při opouštění jeho kroku.

Další související chyby: přidaný celý prázdný řádek účastníka mohl Django formset vynechat; jména měla ve formuláři limit 150, zatímco model objednaného účastníka má 100; povinný souhlas byl pouze klientský; server a klient se lišily při obsazeném `username` s jiným e-mailem.

## Proces a výsledné řešení

| Krok | Přechod a kontrola |
|---|---|
| 1 – Výběr kurzu | §4 pokračuje do online objednávky; §6/§7 a individuální školení zachovávají kontaktní cestu. Přímý POST §6/§7 nadále odmítá stávající URL dekorátor. |
| 2 – Informace | §4 pokračuje k účastníkům; §6/§7 na kontakt. |
| 3 – Účastníci | Pokračovat volá stejný registrační endpoint s `_validate_step=3`: skutečný Django formset včetně všech řádků, syntaxe, délek, duplicit a existujících účtů. |
| 4 – Údaje a platba | `_validate_step=4`: skutečný BillingForm, bez vynucení dosud nezadaného souhlasu. ARES je volitelný, ruční vyplnění zůstává možné. |
| 5 – Shrnutí | `_validate_step=all`: všechny formuláře a souhlas. Po úspěchu samostatný finální POST znovu vše validuje a teprve potom vytvoří objednávku. |

Kontroly s `_validate_step` nikdy nevytvářejí objednávku, fakturu ani e-maily. Zůstávají chráněné CSRF. Nenahrazují finální kontrolu a jejich obejití nesmí obejít serverovou validaci. Nepřibývá veřejný endpoint ani závislost aplikace.

`novalidate` odstraňuje neřízený zásah nativní validace před `submit`. Není to samotná oprava: přechody i finální odeslání nyní používají jednotná serverová pravidla, identifikují konkrétní pole, nejprve otevřou jeho panel a teprve potom zaostří a posunou stránku. Chyba má červené zvýraznění, český text, `aria-invalid` a `aria-describedby`; není rozlišena jen barvou. Obecné chyby formuláře a formsetu se zobrazují v zaměřitelném souhrnu s `role=alert`. Během kontroly se zobrazí stav „Kontroluji údaje…“, akční tlačítka jsou dočasně zakázaná. Výpadek spojení, CSRF chyba, neplatná odpověď i 15sekundový timeout dostanou viditelnou zprávu a možnost opakování. Změny hodnot během čekání zneplatní starý výsledek.

Po opravě hodnoty se odstraní její zastaralá zpráva a související ARIA stav; ostatní chyby zůstávají. Další pokračování opět kontroluje aktuální data. Obnovený koncept v kroku 4/5 ověří i dříve překročené kroky. U odmítnutého POST má přednost serverem vrácený obsah; localStorage jej nepřepisuje. Jiný explicitně požadovaný kurz v URL zachovává možnost přejít na informace tohoto kurzu. Opětovné otevření stejného kurzu zachová rozpracovaný krok.

Přidávání/odebírání dále přeindexovává jména, ID i ARIA reference na souvislé `0..TOTAL_FORMS-1`. Každý skutečně předložený řádek se musí vyplnit, nebo odstranit. Nelze jej tiše vynechat z ceny. Formset hlídá také manipulované indexy a management údaje.

## Pravidla a testovací matice

Nezavádí se kontrola skutečné existence osoby, adresy, e-mailové schránky, telefonu ani daňového subjektu. Nezavádí se nové národní regexy pro DIČ či PSČ ani kontrolní součet IČO. Syntakticky přijatý údaj nemusí skutečně existovat.

| Pole | Pravidlo | Zahrnuté případy |
|---|---|---|
| Jméno a příjmení každého účastníka | Povinné, po ořezu mezer max. 100 znaků podle modelu | Prázdné, mezery, okrajové mezery, 101 znaků, Anna-Marie, diakritika, apostrof |
| E-mail účastníka | Povinný Django EmailField, max. 254; duplicity bez ohledu na velikost písmen; již používaný e-mail nebo username účtu odmítnut | `random`, `a@`, `@example.cz`, `a@firma`, mezery uvnitř, dvě tečky domény, plus v adrese, velká písmena, délka, stejné adresy dvou osob |
| IČO | Nepovinné; při vyplnění přesně 8 ASCII číslic | Prázdné, 7/9 znaků, písmena, směs, jiné Unicode číslice; nic se potají neodstraňuje |
| DIČ | Nepovinné, max. 20, beze změny národních pravidel | Prázdné, CZ i SK podoba, 21 znaků |
| Firma/jméno objednatele | Povinné, max. 255 | Prázdné/mezery, 256 znaků, Čížek & syn – servis, s.r.o., ořez okrajů |
| Ulice | Povinná, max. 255 | Prázdné/mezery, dlouhá hodnota, Nábřeží 12/3 |
| Město | Povinné, max. 120 | Prázdné/mezery, dlouhá hodnota, Frýdek-Místek |
| PSČ | Povinné, max. 20, dosavadní volný formát pro obě země | `70030`, `700 30`, prázdné/mezery, 21 znaků. Abecední text se dosud neodmítá; není zaveden nový národní pattern. |
| Země | Pouze CZ nebo SK | Obě volby; manipulovaná hodnota XX odmítnuta |
| Jméno a příjmení kontaktní osoby | Povinné, max. 100 | Prázdné/mezery, dlouhé, běžné znaky |
| Telefonní předvolba | Povinná, vstup max. 8, po odebrání běžných mezer `+` a 1–7 číslic; plus se doplní | +420, +421, ` 421 `, písmena, samotné +, dvě +, příliš dlouhá |
| Telefon | Povinný, vstup max. 30, po odstranění mezer/pomlček/lomítek alespoň 7 číslic | `777 123 456`, `777-123/456`, písmena, směs, neúplné číslo. Nezavádí se nové ověření přidělení ani devítimístné pravidlo podle země. Předvolba má vlastní pole. |
| Kontaktní e-mail | Povinný Django EmailField, max. 254 | Stejné syntaktické a délkové případy jako účastník; může být shodný s účastníkem |
| Poznámka | Nepovinná, dosavadní TextField bez nového délkového limitu | Prázdná i běžný text; není vymyšlen nový limit |
| Souhlas | Povinný BooleanField, nově kontrolovaný i serverem | Chybějící/odškrtnutý, oprava a následné vytvoření objednávky |
| Celá objednávka/formset | Nejméně 1 úplný účastník, souvislé indexy, správné management údaje | 0 osob, chybějící/nečíselný TOTAL_FORMS, limit formsetu, mezera v indexech, celý prázdný přidaný řádek, více osob a správná cena |

Automatická serverová matice ověřuje každé povinné textové pole s prázdnou hodnotou i samotnými mezerami a každý deklarovaný limit s hodnotou o znak delší. Součástí jsou i POSTy bez JavaScriptu, zachování dat, správné číslo kroku, oprava a následný úspěch, neukládání při validačních požadavcích a CSRF. Stávající ARES testy pokrývají úspěch, nedostupnost, neplatné JSON a ruční cestu nevyžadující ARES.

## Skutečné výsledky a omezení

- Prostředí: Python **3.13.5**, Django **6.0.4**, preview transport. Není to přesně uživatelův Python 3.13.1. Projektové requirements se nemění. Instalace všech jejich přesných verzí zde narazila na chybějící systémové Cairo pro pycairo; pomocné prostředí používá dostupné verze PDF knihoven. Srovnání s výchozím commitem proběhlo ve stejném prostředí.
- Finální cílená sada: **70 testů: 59 skutečně provedených prošlo, 11 browser testů přeskočeno** pro chybějící Playwright browser. Žádný přeskočený test není vykázán jako provedené browser ověření.
- Doplňkový běh JS v jsdom proti skutečnému Django serveru: **9 validačních POSTů a jeden zachycený finální submit**, očekávané kroky, chyby, fokus, opravy i odhalení neplatného skrytého pole. Finální odeslání v této simulaci bylo zachyceno; skutečné vytvoření jednotlivé i skupinové objednávky ověřují serverové testy. Simulace neměří skutečný layout ani konzoli Chromia.
- Celá sada nad výchozím commitem: **322 testů; 302 prošlo, 8 přeskočeno, 9 failures a 3 errors**. Selhávají testy závislé na vystavení PDF a navazujících emailových artefaktech, protože Playwright Chromium není dostupný.
- Finální celá sada nad opravou: **348 testů; 317 prošlo, 19 přeskočeno, 9 failures a 3 errors**. Automatické porovnání názvů všech 12 neúspěšných testů potvrdilo přesnou shodu s výchozím commitem. PDF renderer nebyl nahrazen ani stubován. Po tomto běhu zůstala už jen drobná JS úprava zachovávající i všechny prázdné řádky obnoveného konceptu; následně byla znovu provedena cílená sada a DOM simulace.
- `manage.py check`, `makemigrations --check --dry-run`, `node --check` a `git diff --check`: OK. **Tato oprava nepotřebuje novou migraci.**

Spuštění systémového `/usr/bin/chromium` skutečně selhalo na `socket() failed: Operation not permitted`; stažení Playwright Chrome Headless Shell skončilo poškozeným/neplatným archivem. Desktop, mobil, skutečná konzole, síť v browseru, automatický fokus v Chromiu, Firefox ani WebKit proto **nebyly zde skutečným prohlížečem ověřeny**. Totéž platí pro nový end-to-end průchod až přes PDF a aktivaci. Není vydáváno potvrzení vizuální bezchybnosti ani úspěchu celého produkčního workflow v tomto runtime.

Nová browser regrese má 11 skutečných Playwright scénářů: platné samostatné objednávky desktop/mobil, chyby a opravy polí, mobilní chyby a přetečení, duplicity, neplatné skryté pole při odeslání, skutečné serverové odmítnutí po obejití klienta, obnovení neplatného konceptu, odebrání prostřední osoby/přidání/obnova/cena 2970 Kč, ARES výpadek/ruční údaje/SK, obecná form/formset chyba, výpadek kontroly. Sbírá JS chyby i konzolové „not focusable“. Pro úspěšné běhy jsou požadovány skutečně spuštěné prohlížeče. Původní `test_registration_browser` a `test_portal_navigation_browser` zůstávají k dispozici pro širší průchod včetně platebního odpočtu a aktivace.

## Použití a přesné lokální příkazy

ZIP obsahuje jen změněné a nové soubory s cestami od kořene repozitáře, včetně této zprávy a testů. Rozbalit do aktuální lokální kopie založené na uvedeném commitu; vlastní novější změny nejprve porovnat. Neobsahuje databázi, .env, náhradní renderer ani instalační prostředí. Aktivovat své dosavadní venv, ponechat existující DJANGO_SECRET_KEY a z kořene projektu v PowerShellu spustit:

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test courses.tests.test_checkout_validation courses.tests.test_registration courses.tests.test_registration_order_controls courses.tests.test_frontend_static_assets courses.tests.test_ares
```

Nová migrace se nevytváří. Pokud lokálně dosud nejsou aplikovány starší migrace aktuálního repozitáře (např. 0021), použít standardní:

```powershell
python manage.py migrate
```

Browser kontroly (pokud již Playwright/browser funguje, instalaci neopakovat):

```powershell
python -m pip install playwright
python -m playwright install chromium
# Pokud chcete Playwright Chromium místo vlastního systémového prohlížeče:
Remove-Item Env:CHROMIUM_EXECUTABLE_PATH -ErrorAction SilentlyContinue
python manage.py test courses.tests.test_checkout_validation_browser
python manage.py test courses.tests.test_registration_browser courses.tests.test_portal_navigation_browser
python manage.py test courses
node --check courses/static/courses/js/registration.js
git diff --check
python manage.py runserver
```

Nová browser sada také umožňuje srovnání enginů:

```powershell
python -m playwright install firefox webkit
$env:CHECKOUT_BROWSER = "firefox"
python manage.py test courses.tests.test_checkout_validation_browser
$env:CHECKOUT_BROWSER = "webkit"
python manage.py test courses.tests.test_checkout_validation_browser
Remove-Item Env:CHECKOUT_BROWSER -ErrorAction SilentlyContinue
```

WebKit není potvrzením běhu skutečného Safari na macOS/iOS. Rozdíly nativního HTML email validátoru jsou omezeny tím, že rozhoduje stejný Django validátor pro všechny enginy.

Ruční kontrola navíc: Chrome desktop i mobil (390/320 px), platná skupina, diakritika, velmi dlouhé hodnoty obnovené v konceptu, Enter v jednotlivých polích, obecná chyba a opakování po výpadku spojení. Po opravě dokončit jednu objednávku přes „Přeskočit odpočet…“, druhou nechat přejít po 30 sekundách; ověřit aktivaci, preview e-maily a uloženou fakturu. Zkontrolovat také právní modaly a §6/§7/individuální kontakt. Veškeré průchody dál jen v preview režimu.

PythonAnywhere se nyní nemění. Až po samostatném odsouhlasení commitu, pushe a nasazení platí původní příkaz `bash ~/update_elektroakademie.sh`.

## Oprava testovacích dat po lokálním browser běhu

Uživatel provedl 59 serverových testů úspěšně a 11 skutečných browser testů: 10 prošlo, jeden správně zastavila duplicita v testovacích datech. Při odebrání Boba zůstává Cyrilovi person2@example.invalid; původní helper přidělil stejnou adresu Davidovi na znovu použitém indexu 2. Test nyní Davidovi zadává david@example.invalid a před pokračováním kontroluje jedinečnost všech adres po obnovení. Validační pravidla aplikace se nemění. Syntaxe opraveného testu byla ověřena; opravený browser scénář zde nebyl skutečně spuštěn.
