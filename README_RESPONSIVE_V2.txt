OPRAVA BALÍČKU RESPONSIVITY V2

Původní ZIP chybně obsahoval celý courses/templates/courses/base.html
z veřejné verze repozitáře. Tím mohl přepsat novější commitnuté úpravy
hlavičky VOP/GDPR.

Tento balíček už base.html NEOBSAHUJE.

Postup z kořene repozitáře:
1. Rozbal obsah ZIPu do projektu.
2. Spusť:
   python apply_responsive_fix.py
3. Ověř:
   git diff -- courses/templates/courses/base.html
   git diff --check

Skript načte base.html přímo z aktuálního HEAD a doplní do něj pouze
odkaz na responsive-fixes.css. Zachová tedy commitnuté opravy VOP/GDPR.
