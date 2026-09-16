#!/usr/bin/env python
from pathlib import Path
import re

base = Path("courses/templates/courses/base.html")
if not base.exists():
    raise SystemExit("Spusť skript z kořene repozitáře.")

text = base.read_text(encoding="utf-8")
new, count = re.subn(
    r"(responsive-fixes\.css\?v=)\d+",
    r"\g<1>3",
    text,
)
if count:
    base.write_text(new, encoding="utf-8", newline="")
    print("OK: verze responsive-fixes.css v base.html nastavena na v=3.")
else:
    print("INFO: odkaz na responsive-fixes.css nebyl nalezen; CSS přesto můžeš použít a udělat Ctrl+F5.")
