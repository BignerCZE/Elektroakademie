# Cookies a Google Analytics 4

Výchozí commit: 7f17b61. Bez GA4_MEASUREMENT_ID se Analytics nikdy nenačte.

1. V GA4 vytvořte webový datový stream a zkopírujte ID G-… .
2. V nastavení streamu vypněte celé Vylepšené měření (Enhanced measurement), včetně automatického měření formulářů a historie URL. Implementace posílá pouze vlastní události a očištěné názvy stránek. Google Signals a reklamní personalizaci ponechte vypnuté. Uchování dat událostí nastavte na 2 měsíce. Dokončete smluvní a datové nastavení účtu Google.
3. Do produkčního .env přidejte GA4_MEASUREMENT_ID=G-VAŠESKUTEČNÉID (bez ukázkového ID). Lokálně jej můžete nechat prázdné.
4. Nahrajte soubory, spusťte `python manage.py migrate`, `python manage.py collectstatic --noinput` a reload aplikace. Změna nevyžaduje nové závislosti.
5. Ověřte v anonymním okně: před souhlasem žádné požadavky na Google; odmítnutí zachová objednávku; analytika a média se povolují nezávisle; odvolání zastaví měření a odstraní _ga cookies; na aktivaci, v dashboardu a testech se Analytics nenačítá.

Události: page_view, begin_checkout, checkout_step, order_created (jednorázově po serverovém vytvoření objednávky). Potvrzenou objednávku a platbu evidujte nadále v Django; současná platba je simulovaná, proto ji neoznačujeme jako skutečnou konverzi purchase. Kontaktní formulář zatím nemá serverové odeslání, a proto se nevykazuje falešný lead.

Souhlas je uložen v podepsané HttpOnly cookie na 180 dnů a v tabulce CookieConsent bez IP adresy. Starší záznamy než 365 dnů se promazávají při uložení nové volby.

DŮLEŽITÉ: Stávající privacy_policy.html i legal/privacy_content.html v původním repozitáři obsahují text VOP místo kompletních zásad ochrany osobních údajů. Doplněn odkaz na nové konkrétní informace o cookies. Před ostrým provozem je potřeba samostatně dokončit celkové zásady pro účty, objednávky a školení.

## Ověření této dodávky

- 9/9 nových Django testů a 8/8 JavaScript testů prošlo.
- Celá Django sada: 248/252 prošlo. Stejné čtyři chyby ověřeny i na původním commitu: jeden test očekává staré verze landing.css/landing.js; tři workflow testy zde potřebují dostupné Chromium pro certifikáty. Tyto nesouvisející testy nebyly změněny.
- Django check, kontrola migrací a git diff --check bez problémů.
- Runtime zde má Python 3.12 a Django 5.2.19; projekt cílí na Python 3.13 a Django 6.0.4. Před ostrým nasazením spusťte nové testy i v projektovém prostředí.
- Stažení Chromia se v tomto prostředí nezdařilo; vizuální ověření v reálném prohlížeči zde nebylo dokončeno. Frontendové kontroly používají Node test runner a simulovaný DOM.

Příkazy pro kontrolu: `python manage.py test courses.tests.test_cookies` a `node --test courses/tests/cookies_frontend.test.cjs`.

## Vzhled cookie okna

Okno je uprostřed obrazovky, s pozadím rgba(0, 0, 0, 0.82), stejným jako video na úvodní stránce. Okno nemá křížek. Zavření kliknutím mimo okno nebo klávesou Escape neuděluje nový souhlas. Volitelné služby zůstanou při první návštěvě vypnuté. Okno lze znovu otevřít odkazem Nastavení cookies. Na mobilu má vlastní posouvání.

Informace o cookies i Podrobnosti o cookies se otevírají v témže modálním okně. Obsah sdílí partial legal/cookies_content.html se samostatnou stránkou /cookies/. Informace lze zavřít nebo přejít zpět na nastavení. Po této úpravě prošlo 9 Django a 9 JavaScript testů.

Odkazy Nastavení cookies / Informace o cookies jsou bílé, bez pozadí a rámečku, zarovnané doprostřed u spodního okraje obrazovky.

Odkazy cookies jsou nyní staticky pod kontaktní sekcí v jejím posuvném obsahu; na ostatních stránkách jsou na konci obsahu. Nemají fixní pozici a objeví se až po dorolování.

Oprava rozložení kontaktu: patička je uvnitř původního .contact-inner, pod .contact-wrapper. Kontakt má opět jediný přímý blok v řádkovém flexboxu, takže se jeho šířka nedělí s patičkou. Struktura umístění ověřena HTML parserem.

Aktuální chování nastavení: při první návštěvě jsou podrobné volby skryté. Tlačítko Nastavení je rozbalí, Skrýt nastavení je opět skryje bez ztráty rozpracovaného výběru. Odkaz v patičce otevře rovnou uložené volby. Zavřít bez rozhodnutí neukládá novou volbu a nepovoluje nové služby. Ověřeno 12 frontendovými testy.
