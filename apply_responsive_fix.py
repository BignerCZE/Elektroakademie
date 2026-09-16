#!/usr/bin/env python
from pathlib import Path
import re
import subprocess
import sys

BASE = Path("courses/templates/courses/base.html")
LINK = '<link rel="stylesheet" href="{% static \'courses/css/responsive-fixes.css\' %}?v=2">'

def git_head_file(path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise SystemExit(
            "Nepodařilo se načíst base.html z HEAD. Spusť skript z kořene repozitáře."
        )
    return result.stdout

# Vždy vycházíme z commitnuté verze base.html, takže se nevrátí starší
# navigace právních stránek z předchozího ZIPu.
original = git_head_file(BASE.as_posix())
text = original.decode("utf-8")

if "responsive-fixes.css" not in text:
    # Preferujeme vložení hned za blok extra_css.
    pattern = re.compile(
        r"({%\s*block\s+extra_css\s*%}.*?{%\s*endblock(?:\s+extra_css)?\s*%})",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        insert_at = match.end()
        newline = "\r\n" if "\r\n" in text else "\n"
        text = text[:insert_at] + newline + LINK + text[insert_at:]
    else:
        # Bezpečný fallback: vložení před </head>.
        m = re.search(r"</head\s*>", text, flags=re.IGNORECASE)
        if not m:
            raise SystemExit(
                "V base.html nebyl nalezen blok extra_css ani </head>. "
                "Soubor nebyl změněn."
            )
        newline = "\r\n" if "\r\n" in text else "\n"
        text = text[:m.start()] + LINK + newline + text[m.start():]

BASE.write_text(text, encoding="utf-8", newline="")
print("OK: base.html obnoven z HEAD a doplněn pouze responsive-fixes.css.")
print("OK: předchozí úpravy VOP/GDPR z commitnuté verze zůstaly zachovány.")
