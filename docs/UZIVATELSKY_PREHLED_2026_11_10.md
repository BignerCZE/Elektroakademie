# Jednotný uživatelský přehled – 10. 11. 2026

## Základ a rozsah

Balíček navazuje na předchozí odsouhlasené úpravy kontroly testu, certifikátu, aktivace a administrace faktur, včetně opravy vláken v browser testech. Při ověření vzdáleného repozitáře byl origin/main stále na fa18bb3db6511d3b8cf7278a11da20ef84dc3e40; místní pracovní kopie obsahuje zachované předchozí úpravy. Neproběhl commit, push ani nasazení. ZIP obsahuje pouze soubory změněné touto navazující úpravou; předchozí balíček musí být již nainstalovaný.

## Výsledek

- Levé menu uživatelské části obsahuje Přehled, Mé údaje a odhlášení. Video, Test a Certifikát jsou dostupné přímo v přehledu.
- Horní lišta uživatelské části obsahuje vycentrované logo bez navigace a tlačítka „Přejít na Online Kurz“. Úvodní veřejná stránka se nemění.
- Odhlášení je formulář POST s CSRF ochranou. Stávající LOGOUT_REDIRECT_URL již směřuje na `/`; konfigurace se nemění.
- Přehled obsahuje náhled videa, pravý panel testu s historií a spodní kartu certifikátu. Na užších obrazovkách se obsah řadí pod sebe.
- Video používá existující lokální náhled a stejné YouTube video jako homepage (J_eSsfNwDVw). Otevře se v nativním modálním dialogu se zatmaveným pozadím. Bez souhlasu s externími médii se iframe nevytvoří a otevře se nastavení cookies. Zavření křížkem, Escape nebo kliknutím na pozadí odstraní iframe, zastaví přehrávání a vrátí fokus na spouštěcí tlačítko.
- Test lze zahájit POST formulářem přímo v přehledu nebo pokračovat v rozpracovaném pokusu původním endpointem. Po neúspěchu je nabízen nový pokus; po úspěchu kontrola odpovědí. Rozpracovaný pokus má stejně jako dříve přednost před stavem splněného testu.
- Historie obsahuje jen dokončené pokusy aktuálního uživatele a kurzu, od nejnovějších. Zobrazuje datum, číslo pokusu, výsledek, procenta a odkaz na odpovědi. Má omezenou výšku, vlastní svislý scroll a overscroll-behavior: contain. Je dostupná i klávesnicí. Na mobilu se celá stránka běžně posouvá, dlouhá historie zůstává uvnitř svého kontejneru.
- Certifikát se zobrazuje jen oprávněnému uživateli se skutečně existujícím dokladem. Náhled používá původní sdílenou šablonu v překryvném dialogu; zachovává logo, obsah a podpis 22 mm. Na mobilu je A4 dokument uvnitř dialogu posouvatelný, nezužuje se ani nemění rozměry tiskového dokumentu.
- Tlačítko Stáhnout PDF používá původní chráněný endpoint s `?download=1`, který vrací Content-Disposition: attachment. Bez parametru zůstává původní inline chování.
- U účtu se splněným testem, ale bez vystaveného certifikátu (například ruční administrativní účet), se zobrazí pravdivý stav bez nefunkčního odkazu. Pouhé zobrazení přehledu certifikát nevystavuje.
- Původní adresy videa, testů a certifikátů zůstávají funkční. Oprávnění, objednávky, faktury, číselné řady a generování dokumentů se nemění. SMTP ani skutečná brána se nepřipojují.

## Ověření

- Cílená sada: 45/45 OK (nový přehled, aktivace, přístupová práva a certifikát).
- Širší sada: 311 testů, OK se 6 přeskočenými browser testy; 305 provedených testů prošlo. Pouze v dočasném ověřovacím harnessu byl Chromium HTML→PDF renderer nahrazen WeasyPrintem. Aplikace a requirements tuto náhradu neobsahují. Tento výsledek nenahrazuje ověření produkčního PDF rendereru.
- Dva nové browser testy jsou připravené, ale nebyly zde provedeny kvůli chybějícímu Playwright Chromiu. Zahrnují video/souhlasy/zavření, odhlášení, logo, rozměry 1440/1024/768/390/320, vnitřní scroll, náhled certifikátu a PDF download (v browser testu s testovacími PDF bajty).
- Dva dřívější testy byly přizpůsobeny přesunu videa: místo odkazu Video v sidebaru ověřují tlačítko videa přímo v přehledu. Je zachovaná dřívější oprava všech ORM operací mimo asynchronní vlákno Playwrightu.
- Django check, makemigrations --check --dry-run, JS syntax a git diff --check: OK.
- Pomocné prostředí Python 3.13.5 / Django 6.0.4. Plné vizuální ověření v prohlížeči a standardní kompletní sadu proveďte lokálně. Nová databázová migrace ani změna závislostí není potřeba.

## Lokální použití

Zálohujte vlastní rozpracované změny. ZIP rozbalte do kořene projektu a zachovejte strukturu adresářů. Obsahuje 11 souborů včetně této dokumentace. Pokud máte vlastní pozdější úpravy dotčených souborů, nejprve je porovnejte.

V aktivovaném virtuálním prostředí v PowerShellu:

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test courses.tests.test_portal_overview
python manage.py test courses.tests.test_portal_overview_browser
python manage.py test courses
python manage.py runserver
```

Playwright Chromium u vás již fungoval při předchozích 302 testech. Pokud by v jiném prostředí chyběl, použijte `python -m playwright install chromium`. Nové migrace nejsou potřeba; dřívější 0021 zůstává aplikovaná.

## Ruční kontrola

1. V přehledu ověřte pouze dvě navigační položky a odhlášení vlevo, logo uprostřed horní lišty a absenci horních tlačítek.
2. Bez souhlasu s externími médii klikněte na video: nabídne cookies, nezačne přehrávat. Po udělení souhlasu spusťte video, zavřete jej křížkem, Escape i kliknutím na pozadí; přehrávání se musí zastavit. Externí video se zde automaticky netestuje síťovým přehráním.
3. Ověřte nový test, rozpracovaný test, neúspěšný pokus i úspěšné splnění. Odkaz na odpovědi musí otevřít vlastní dokončený pokus. Dlouhou historii posouvejte kolečkem i klávesnicí uvnitř jejího panelu.
4. Se skutečným certifikátem otevřete náhled a zavřete jej. Stáhnout PDF musí nabídnout soubor. Před splněním testu ani při chybějícím dokladu nesmí být nefunkční tlačítka.
5. Zkontrolujte desktop i telefon. Na mobilu se obsah řadí video → test/historie → certifikát. A4 v náhledu lze posouvat uvnitř okna, samotná stránka se nesmí roztahovat do šířky.
6. Odhlaste se z levého menu: návrat má být na homepage, přímý návrat na dashboard vyžaduje přihlášení.

Commit, push ani nasazení nejsou součástí této dodávky. Pro pozdější schválenou aktualizaci PythonAnywhere zůstává `bash ~/update_elektroakademie.sh`; nové statické soubory vyžadují collectstatic a reload.
