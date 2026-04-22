# Changelog

## [1.0.0] - 2026-04-16

### Přidáno

* Django projekt Elektroakademie
* Registrace, přihlášení a odhlášení uživatelů
* Vlastní model CustomUser (is_paid, passed_quiz)
* Administrace přes Django admin
* Modely Course, Question, Choice, Payment
* Seznam kurzů na homepage
* Detail kurzu
* Simulace platby (nastavení is_paid)
* Ochrana obsahu podle přihlášení a platby
* Stránka s videem kurzu
* Kvízový systém
* Vyhodnocení testu (procenta, splnění)
* Náhodný výběr otázek z databáze
* HTML certifikát o dokončení
* Generování PDF certifikátu (xhtml2pdf)
* Profil uživatele

### Změněno

* Kvíz nyní vybírá náhodný počet otázek (nastavitelné v settings.py)
* Minimální úspěšnost testu nastavena přes settings.py

### Opraveno

* Skrytí video URL pro nepřihlášené uživatele
* Oprava migrací při zavedení CustomUser
