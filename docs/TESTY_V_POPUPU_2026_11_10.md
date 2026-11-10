# Odpovědi a historie ve společném okně

Navazující balíček pro poslední kompaktní uživatelský přehled. Rozbalit do kořene projektu se zachováním struktury. Obsahuje 10 změněných a nových souborů včetně této dokumentace. Při vlastních změnách dotčených souborů nejprve porovnat rozdíly.

## Chování

- „Zobrazit odpovědi“ i „Historie testů“ mají stejnou bílou řádkovou podobu s rámečkem a zvýrazněním jako FAQ. Otevírají stejné překryvné okno ve stylu FAQ.
- Přímé „Zobrazit odpovědi“ z přehledu otevře první otázku nejlepšího pokusu stejně jako dřívější přímý odkaz. V historii lze vybrat libovolný vlastní dokončený pokus.
- Detail se načítá do stejného okna. Funguje výběr čísla otázky, Předchozí otázka, Další otázka, zobrazení zvolené/správné/špatné odpovědi i návrat do historie. První otázka nemá předchozí a poslední nemá následující odkaz.
- Horní tlačítko „Zpět na historii“ a spodní „Zpět na historii testů“ vrací seznam ve stejném okně. Pozice posunu seznamu se zachovává a fokus se vrací na otevřený pokus.
- URL přehledu se při běžném procházení popupu nemění, stránka na pozadí neroluje. Zavření funguje tlačítkem, Escape a kliknutím mimo okno. Po zavření se fokus vrátí na původní spouštěcí prvek.
- Během načítání je zobrazen stav; při chybě nebo vypršení přihlášení zůstane srozumitelná zpráva s dostupným návratem do historie. Zavření nebo přepnutí zruší předchozí požadavek a jeho opožděný výsledek nesmí přepsat nové zobrazení.

## Implementace a bezpečnost

Samostatná stránka a popup používají společnou šablonu `quiz_attempt_content.html`; obsah odpovědí se neduplikuje. Existující `quiz_attempt_detail` podporuje `?fragment=1`, který po původní kontrole vlastníka a dokončení vrátí pouze obsah, s no-store a potvrzovací hlavičkou X-Quiz-Review-Fragment. JavaScript přijímá pouze odpověď se správnou hlavičkou ze stejného originu; přesměrování na přihlášení se nevloží do okna jako obsah testu. Uživatelský obsah se nadále escapuje v Django šabloně.

Původní detailní URL zůstává funkční a bez JavaScriptu či při otevření odkazu v nové kartě zobrazuje samostatnou stránku. Samotný popup žádný nový pokus nevytváří ani nemění odpovědi. Výukové video, souhlasy, certifikáty, faktury a oprávnění se nemění.

## Ověření

- Cílená sada 25/25 OK: fragmenty první/střední/poslední otázky, ochrana cizího a nedokončeného pokusu, nepřihlášený přístup, zachovaný samostatný detail, přehled a stávající přístupy.
- Django check, makemigrations --check --dry-run, syntaxe JS a git diff --check: OK.
- Tři browser testy byly zde přeskočené, protože není dostupné Playwright Chromium. Nová regrese přímo kontroluje otevření odpovědí, přepnutí 1→2→1→3, první/poslední navigaci, návrat do historie, otevření pokusu ze seznamu, zavření a neměnnou URL přehledu. Je nutné ji spustit lokálně.
- Nová databázová migrace ani závislost není potřeba. Odkazy na CSS a JS mají verzi 3 pro obnovu cache.

## Lokální ověření

```powershell
$env:EMAIL_TRANSPORT = "preview"
python manage.py check
python manage.py test courses.tests.test_quiz_review_popup courses.tests.test_quiz_review courses.tests.test_portal_overview courses.tests.test_portal_overview_browser
python manage.py runserver
```

Po obnovení stránky Ctrl+F5 vyzkoušet obě hlavní akce. V okně historie vybrat pokus, přepínat otázky v obou směrech i přes čísla, vrátit se na seznam a zvolit jiný pokus. Přehled musí zůstat na pozadí bez přechodu na novou stránku. Zkontrolovat také mobil a chybějící dokončené pokusy.

Commit, push ani nasazení nebyly provedeny.
