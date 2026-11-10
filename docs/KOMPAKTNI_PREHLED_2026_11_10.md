# Kompaktní přehled: historie v okně a certifikát u testu

Navazuje na balíček elektroakademie_novy_prehled_2026_11_10.zip. Nejprve musí být nainstalovaný předchozí sjednocený přehled. Tento ZIP obsahuje jen sedm navazujících změněných souborů včetně této dokumentace. Před přepsáním souborů zachovejte své případné další lokální úpravy.

## Co se změnilo

- Přehled má dvě hlavní části: video vlevo a test s certifikátem vpravo. Certifikát je součástí panelu testu, oddělený jen jemnou čárou.
- Trvalý výpis historie byl nahrazen tlačítkem „Historie testů“ s počtem pokusů. Historie se načítá ze stejných vlastních pokusů jako dosud.
- Okno historie vizuálně odpovídá FAQ z homepage: šířka do 1100 px, výška do 86 % obrazovky, zaoblení 24 px, bílé pozadí, pevná hlavička, tlačítko Zavřít a zatmavené rozostřené pozadí. Posouvá se pouze obsah historie. Funguje Escape, kliknutí mimo okno a návrat fokusu na tlačítko.
- Zmenšeny mezery, vnitřní odsazení a výška náhledu videa. Panely se již neroztahují na celou výšku viewportu. Výpočet výšky přehledu počítá také s 45px desktopovou patičkou cookies.
- Kompaktní rozložení platí pouze pro Přehled; ostatní stránky uživatelské části a veřejná homepage se nemění. Na telefonu či při menší výšce okna zůstává běžné rolování stránky dostupné; obsah se neodřezává.
- Přehrávání, souhlasy cookies, testy, přístupová práva, náhled/stahování certifikátu ani faktury se nemění. Úprava JS pouze omezuje přepočet sazby certifikátu na okno s certifikátem, nikoli historii.
- Odkazy na upravené CSS a JS mají verzi 2 pro obnovu cache.

## Ověření

- Cílené serverové testy: 40/40 OK (přehled včetně nového umístění historie/certifikátu, aktivace a přístupy).
- Django check, makemigrations --check --dry-run, git diff --check a syntaxe upraveného JS: OK.
- Dva browser testy zde byly přeskočené kvůli chybějícímu Playwright Chromiu. Upravená browser regrese kontroluje absenci svislého scrollu při 1920×1080, 1440×900 a 1366×768, vodorovný rozměr od 1440 do 320 px, logo, otevření/zavření historie a scroll uvnitř okna. Obsahuje také dosavadní kontrolu videa, certifikátu, stažení a odhlášení.
- Vizuální výsledek a skutečné rozměry v Chromiu zde nejsou potvrzené. Záměrně není použit overflow:hidden na celou stránku, aby při dlouhých údajích, zvětšení textu či malé výšce okna zůstal všechen obsah dosažitelný.

## Použití

Rozbalte ZIP do kořene projektu se zachováním adresářové struktury. Nové migrace ani závislosti nejsou potřeba.

V aktivovaném prostředí v PowerShellu:

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py test courses.tests.test_portal_overview courses.tests.test_portal_overview_browser
python manage.py runserver
```

Zkontrolujte přehled při běžném desktopovém rozlišení: stránka má být bez nutnosti posouvání, historie má být ukrytá do kliknutí a certifikát v panelu testu. V historii ověřte otevření odpovědí, zavření tlačítkem, Escape a kliknutím na pozadí. Na mobilu zkontrolujte běžné posouvání stránky a samostatný scroll historie v okně. Pokud vidíte starou podobu, obnovte stránku Ctrl+F5.

Žádný commit, push ani nasazení nebyly provedeny.
