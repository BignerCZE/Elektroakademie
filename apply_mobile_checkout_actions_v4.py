from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "courses/static/courses/js/registration.js"
CSS = ROOT / "courses/static/courses/css/responsive-fixes.css"
BASE = ROOT / "courses/templates/courses/base.html"

for path in (JS, CSS, BASE):
    if not path.exists():
        raise SystemExit(f"CHYBA: Nenalezen soubor {path}. Spusť skript z kořene repozitáře.")

js = JS.read_text(encoding="utf-8")

target_marker = '    const finalOrderActionCard = document.getElementById("final-order-action-card");\n'
if target_marker not in js:
    raise SystemExit("CHYBA: registration.js neodpovídá očekávanému stavu.")

insert = '''    const mobileCheckoutNextButton = document.createElement("button");
    mobileCheckoutNextButton.type = "button";
    mobileCheckoutNextButton.id = "mobile-checkout-next-button";
    mobileCheckoutNextButton.className = "mobile-checkout-next-button";
    mobileCheckoutNextButton.hidden = true;

    if (checkoutBackButton && checkoutBackButton.parentNode) {
        checkoutBackButton.parentNode.insertBefore(mobileCheckoutNextButton, checkoutBackButton);
    }

    function getMobileCheckoutTarget(step) {
        if (step === 2) return goToParticipantsButton;
        if (step === 3) return participantsToBillingButton;
        if (step === 4) return goToFinalSummaryButton;
        if (step === 5 && finalOrderActionCard) {
            return finalOrderActionCard.querySelector('button[type="submit"], input[type="submit"]');
        }
        return null;
    }

    function updateMobileCheckoutAction(step) {
        const target = getMobileCheckoutTarget(step);

        if (!target) {
            mobileCheckoutNextButton.hidden = true;
            mobileCheckoutNextButton.disabled = false;
            mobileCheckoutNextButton.textContent = "";
            return;
        }

        mobileCheckoutNextButton.hidden = false;
        mobileCheckoutNextButton.disabled = Boolean(target.disabled);
        mobileCheckoutNextButton.textContent =
            (target.textContent || target.value || "Pokračovat").trim();
    }

    mobileCheckoutNextButton.addEventListener("click", function () {
        const step = Number(document.body.dataset.checkoutStep || "1");
        const target = getMobileCheckoutTarget(step);

        if (target && !target.disabled) {
            target.click();
        }
    });

'''

if "function getMobileCheckoutTarget(step)" not in js:
    js = js.replace(target_marker, target_marker + insert, 1)

showstep_marker = '        goToFinalSummaryButton.hidden = step !== 4;\n'
if showstep_marker not in js:
    raise SystemExit("CHYBA: showStep blok nebyl nalezen.")

if "        updateMobileCheckoutAction(step);\n" not in js:
    js = js.replace(showstep_marker, showstep_marker + '        updateMobileCheckoutAction(step);\n', 1)

observer_anchor = '    if (addButton) {\n'
observer_code = '''    [
        goToParticipantsButton,
        participantsToBillingButton,
        goToFinalSummaryButton
    ].filter(Boolean).forEach(function (button) {
        new MutationObserver(function () {
            updateMobileCheckoutAction(Number(document.body.dataset.checkoutStep || "1"));
        }).observe(button, {
            attributes: true,
            childList: true,
            subtree: true
        });
    });

    if (finalOrderActionCard) {
        new MutationObserver(function () {
            updateMobileCheckoutAction(Number(document.body.dataset.checkoutStep || "1"));
        }).observe(finalOrderActionCard, {
            attributes: true,
            childList: true,
            subtree: true
        });
    }

'''

if observer_anchor not in js:
    raise SystemExit("CHYBA: anchor pro observer nebyl nalezen.")

if "].filter(Boolean).forEach(function (button) {" not in js:
    js = js.replace(observer_anchor, observer_code + observer_anchor, 1)

JS.write_text(js, encoding="utf-8", newline="\n")

css = CSS.read_text(encoding="utf-8")
css_patch = '''

/* Mobile checkout: primary action stays visible together with Back. */
.mobile-checkout-next-button {
    display: none;
}

@media (max-width: 640px) {
    .checkout-steps {
        align-items: stretch;
    }

    .mobile-checkout-next-button {
        order: 2;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-width: 0;
        min-height: 48px;
        padding: 8px 18px;
        border: 0;
        border-radius: 999px;
        background: var(--color-bg-mid);
        color: #ffffff;
        font: inherit;
        font-weight: 700;
        line-height: 1.2;
        text-align: center;
        cursor: pointer;
    }

    .mobile-checkout-next-button:hover {
        background: var(--color-bg-end);
    }

    .mobile-checkout-next-button:disabled {
        opacity: 0.58;
        cursor: wait;
    }

    .mobile-checkout-next-button[hidden] {
        display: none;
    }

    .checkout-back-button {
        order: 3;
    }
}
'''

if "Mobile checkout: primary action stays visible together with Back." not in css:
    CSS.write_text(css.rstrip() + css_patch + "\n", encoding="utf-8", newline="\n")

b = BASE.read_bytes()
idx = b.find(b"responsive-fixes.css")
if idx != -1:
    ver = b.find(b"?v=3", idx)
    if ver != -1:
        b = b[:ver] + b"?v=4" + b[ver + 4:]
BASE.write_bytes(b)

print("OK: mobilní tlačítko pokračování bylo přidáno do sticky navigace.")
print("OK: desktop zůstává beze změny.")
print("OK: cache responsive CSS zvýšena na v=4, pokud byla nalezena.")
