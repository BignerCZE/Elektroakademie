from pathlib import Path

p = Path("courses/templates/courses/base.html")
b = p.read_bytes()

needle = b"        {% block extra_css %}{% endblock %}"

if needle not in b:
    raise SystemExit("CHYBA: extra_css block nenalezen.")

if b"responsive-fixes.css" in b:
    raise SystemExit("CHYBA: responsive-fixes.css uz v base.html je.")

newline = b"\r\n" if b"\r\n" in b else b"\n"

addition = (
    newline
    + b'        <link rel="stylesheet" href="{% static \'courses/css/responsive-fixes.css\' %}?v=3">'
)

b = b.replace(needle, needle + addition, 1)
p.write_bytes(b)

print("OK: responsive-fixes.css?v=3 pridan bez zmeny kodovani.")
