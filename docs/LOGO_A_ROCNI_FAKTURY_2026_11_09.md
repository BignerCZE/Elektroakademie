# Roční číslování faktur a logo bez sloganu

Stav připravených změn k 9. 11. 2026. Zdrojový repozitář: main / 4e788f0e7ab60666770ef8fb3218e55f05ce867d. Tento balíček navazuje na předchozí fakturační balíček a obsahuje i jeho soubory, protože na GitHubu dosud nejsou.

## Co je upraveno

- Nové faktury mají číslo YY30NNNN: 26300001, 26300002, …, 26309999. Každý rok začíná od 0001, měsíc pořadí nemění. Rok se počítá podle Europe/Prague.
- Číslování zůstává chráněné transakcí a zápisovým zámkem SQLite, databázovou unikátností čísla, vazbou 1:1 na objednávku a unikátní dvojicí období/pořadí.
- Již vystavené měsíční faktury se nepřečíslují. Starší období 202611 mohou zůstat vedle nového ročního období 2026. Úspěšně uložená PDF a snapshoty zůstávají beze změny. Proto zůstala maximální délka databázového čísla 9 a období 6; nové hodnoty jsou kratší. Není potřeba měnit schéma ani existující migrační soubor 0020.
- Nové faktury používají logo courses/static/courses/img/svetle_pozadi_bez_sloganu.svg. Odkaz je změněn také v HTML náhledu certifikátu i v jeho PDF rendereru. Logo na ostatních stránkách se nemění.
- Starší vystavené faktury si zachovávají své uložené logo a PDF. U certifikátů se nová varianta loga projeví při jejich dalším zobrazení nebo generování.

## Logo a kontrola dokumentů

Skutečné logo bylo staženo z commitu 4e788f0. V původním SVG byla grafika obklopena velkou prázdnou plochou (plátno 1024 × 768), která zbytečně zvětšovala hlavičku a posunula podpisy certifikátu na druhou stránku. Změnily se pouze rozměry kořenového SVG a viewBox na 32.5 326.5 958 115; cesty, barvy ani vložená grafika se nemění. Ořez má kolem viditelného obsahu rezervu.

Oříznuté SVG je součástí ZIPu na cestě courses/static/courses/img/svetle_pozadi_bez_sloganu.svg. Faktura i certifikát byly vytvořeny skutečným projektovým Chromium rendererem s tímto logem a prohlédnuty po rasterizaci. Obě ukázky mají jednu stranu A4 a používají pouze testovací údaje.

## Použití v lokálním projektu

Zálohujte databázi a zkontrolujte vlastní rozpracované změny. ZIP obsahuje celé změněné soubory pro uvedený základ; nepřepisujte jím vlastní pozdější úpravy naslepo. Rozbalte do kořene Elektroakademie a zachovejte adresářovou strukturu. Oříznuté SVG je již přiloženo; ve virtuálním prostředí spusťte v PowerShellu:

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

Přímé nasazení, commit ani push v této dodávce neproběhly. Po ověření a přenesení změn včetně oříznutého SVG na GitHub použijte svůj zavedený příkaz:

```bash
bash ~/update_elektroakademie.sh
```

Skript musí provést migrate, collectstatic a reload. Bez přenesení změn na GitHub tento příkaz sám připravené soubory nezíská. Není připojena skutečná platební brána a nebyly odeslány skutečné e-maily.

## Provedené kontroly

- Celá Django sada se skutečným novým SVG: 289/289 OK, 63,153 s, Python 3.13.17 / Django 6.0.4, Playwright 1.55.0 / Chromium 140. Žádná záměna za testovací logo.
- Po oříznutí prázdné plochy SVG byly faktura a certifikát znovu skutečně vyrenderovány a vizuálně zkontrolovány. Faktura má číslo 2600001; oba dokumenty mají 1 × A4 a čitelnou diakritiku, logo a kompletní obsah včetně podpisů certifikátu.
- Cílené fakturační a certifikační testy byly znovu spuštěny s finálním oříznutým SVG.
- Django check, makemigrations --check --dry-run a git diff --check: OK. Změna schématu oproti předchozímu fakturačnímu balíčku není potřeba.
- Nebyly odeslány skutečné e-maily, připojena platební brána ani provedeny commit/push či nasazení na PythonAnywhere.

## Zvětšení loga na faktuře

Na přání uživatele je logo na faktuře zvětšeno ze 155 na 290 CSS pixelů (s omezením na 46 % šířky hlavičky). Certifikát se nemění. Nová ukázka faktury byla znovu vyrenderována a vizuálně ověřena jako jedna A4 bez překryvu s nadpisem. Jde pouze o úpravu stylu; obchodní logika ani číslování se nemění.

## Větší podpis revizního technika

Zobrazení podpisu Jakuba Jiráka bylo zvětšeno z maximální výšky 11 na 16 mm (přibližně +45 %); podpisové řádky mají odpovídající prostor. Zdrojový obrázek signature_jakub_jirak.png zůstává zachovaný. Změna sdíleného CSS platí pro náhled, tisk i PDF. Odkazy na CSS mají novou verzi pro obnovu cache. Finální PDF bylo skutečně vyrenderováno, ověřeno jako jedna A4 a vizuálně prohlédnuto včetně kompletní patičky.

## Další zvětšení podpisu

Finální maximální výška podpisu je 22 mm místo předchozích 16 mm, tedy dvojnásobek původních 11 mm. Byly zmenšeny prázdné mezery u dat a podpisové části a dolní vnitřní okraj z 8 na 6 mm; velikosti textů zůstávají stejné. CSS pro náhled má verzi 3. Nové PDF bylo vyrenderováno, prohlédnuto včetně celé patičky a ověřeno jako jedna A4 bez překryvů.

## Finální formát čísla s identifikátorem účetního

Aktuální formát je YY30NNNN. YY je dvoumístný rok podle Europe/Prague, 30 je pevná identifikace pro účetního a NNNN je čtyřmístné roční pořadí 0001–9999. Příklady: 26300001, 26300002, v novém roce 27300001. Měsíc číslo nemění.

Používá se stejná roční číselná řada, proto po dříve vystavené faktuře 2600001 následuje nová 26300002, nikoli reset čítače. Starší sedmimístné ani měsíční doklady, jejich snapshoty a uložená PDF se nepřepisují. Databázové pole zůstává dostatečně dlouhé pro starší čísla; nová migrace není potřeba. Při vyčerpání 9999 se vystavení zastaví, číslo se nezkracuje ani nepřetáčí.

Ověření po této změně: fakturační sada 21/21 OK včetně souběhu, ročních přechodů, limitu čtyř míst, pevného identifikátoru a zachování staré roční faktury i PDF. Makemigrations --check --dry-run a git diff --check bez problémů. Ukázka 26300001 byla skutečně vyrenderována a vizuálně zkontrolována jako jedna A4. Podpis na certifikátu zůstává ve schválené velikosti 22 mm.
