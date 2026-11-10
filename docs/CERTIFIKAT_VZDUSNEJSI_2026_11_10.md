# Certifikát – odstranění seznamu činností a větší text

Z aktuální sdílené šablony certificate_document.html byl odstraněn celý oddíl „Rozsah činností, které může osoba poučená zejména vykonávat“, včetně všech šesti bodů a–f. Ostatní obsah zůstává: osobní údaje, ručně vyplňovaná pole rozsahu/pracoviště, obsah poučení, podmínky, data a podpisy.

Základní text se zvětšil z 8,3 na 9,4 pt a řádkování z 1,17 na 1,28. Zvětšeny byly rozestupy v tabulce, mezi odstavci, v ručně vyplňovaných polích a v podpisové části. Vodorovné vnitřní okraje jsou 12 mm místo 10 mm, mezera mezi dvěma ručními poli 8 mm místo 5 mm a mezi podpisy 7 mm místo 5 mm. Logo zůstává, maximální výška podpisu revizního technika je stále 22 mm. Úprava sdílené šablony a CSS platí pro náhled, tisk i nově generované PDF.

Přiložené PDF a PNG obsahují jen testovací údaje. PDF bylo skutečně vyrenderováno z projektové šablony a CSS pomocí WeasyPrint 70.0, zkontrolováno jako jedna A4 a vizuálně ověřeno po rasterizaci. Nejde o výstup projektového Chromium rendereru, který zde není dostupný. WeasyPrint se do aplikace ani jejích requirements nepřidává; slouží pouze pro tento náhled. Jemné rozdíly sazby a skutečný projektový export je nutné ověřit lokálně. Původní automatický kompaktní režim pro výjimečně dlouhé údaje zůstává zachovaný.

## Použití

ZIP obsahuje sedm změněných/nových souborů včetně této dokumentace. Rozbalit do kořene aktuálního projektu. Nová migrace ani závislost není potřeba. Verze odkazu na certificate.css je 4 pro obnovení cache v náhledu a tisku.

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py test courses.tests.test_certificate_document courses.tests.test_certificates
python manage.py runserver
```

Po Ctrl+F5 ověřit náhled certifikátu, tisk a stažení skutečného PDF v projektu. Zkontrolovat jednu A4 a celý podpis/patičku. Úprava nepřepisuje faktury ani jejich uložená PDF a neprovádí žádné změny dat či platnosti existujících certifikátů.

Ověření: 20/20 cílených testů OK, Django check a git diff --check OK. Commit, push ani nasazení nebyly provedeny.
