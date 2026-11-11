"""Real browser checks, never DOM simulations.

EMAIL_TRANSPORT=preview python manage.py test courses.tests.test_checkout_validation_browser
Optional: CHECKOUT_BROWSER=firefox or webkit (install that Playwright engine first).
CHROMIUM_EXECUTABLE_PATH may select a locally installed Chromium.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import close_old_connections
from django.test import override_settings
from django.urls import reverse
from playwright.sync_api import sync_playwright, expect, Error

from courses.forms import BillingForm
from courses.models import Order, OrderParticipant
from courses.tests import test_registration


@override_settings(EMAIL_TRANSPORT="preview", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CheckoutValidationBrowserTests(StaticLiveServerTestCase):
    def db(self, operation):
        def run():
            close_old_connections()
            try:
                return operation()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(run).result(timeout=15)

    def setUp(self):
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        engine_name = os.getenv("CHECKOUT_BROWSER", "chromium")
        engine = getattr(self.pw, engine_name)
        options = {}
        if engine_name == "chromium" and os.getenv("CHROMIUM_EXECUTABLE_PATH"):
            options["executable_path"] = os.environ["CHROMIUM_EXECUTABLE_PATH"]
        try:
            self.browser = engine.launch(**options)
        except Error as error:
            if "Executable doesn't exist" in str(error):
                self.skipTest(f"Install Playwright {engine_name}; no browser verification performed.")
            raise
        self.addCleanup(self.browser.close)
        self.context = self.browser.new_context(viewport={"width": 1366, "height": 900})
        self.context.route("**/*", lambda route: route.continue_()
            if route.request.url.startswith(self.live_server_url) else route.abort())
        self.page = self.context.new_page()
        self.js_errors = []
        self.focus_errors = []
        self.page.on("pageerror", lambda error: self.js_errors.append(str(error)))
        self.page.on("console", lambda message: self.focus_errors.append(message.text)
            if "not focusable" in message.text else None)
        self.open_order()

    def tearDown(self):
        if hasattr(self, "js_errors"):
            self.assertEqual(self.js_errors, [])
            self.assertEqual(self.focus_errors, [])
        super().tearDown()

    def open_order(self):
        self.page.goto(self.live_server_url + reverse("register") + "?course=4")
        reject = self.page.locator('[data-cookie-choice="none"]')
        if reject.is_visible():
            reject.click()
        expect(self.page.locator('[data-step-panel="2"]')).to_be_visible()
        self.action("#go-to-participants-button")
        self.step(3)

    def step(self, number):
        expect(self.page.locator(f'[data-step-panel="{number}"]')).to_be_visible()

    def action(self, selector):
        # Desktop and mobile share the same action through the mobile proxy.
        target = self.page.locator(selector)
        if target.is_visible():
            target.click()
        else:
            self.page.locator("#mobile-checkout-next-button").click()

    def fill_person(self, index=0, first="Anna-Marie"):
        for name, value in {"first_name": first, "last_name": "Čížková",
                "email": f"person{index}@example.invalid"}.items():
            self.page.locator(f'[name="participants-{index}-{name}"]').fill(value)

    def fill_billing(self):
        data = test_registration.RegistrationTests().get_registration_data()
        for name in BillingForm.base_fields:
            locator = self.page.locator(f'[name="{name}"]')
            if name == "country":
                locator.select_option(data[name])
            else:
                locator.fill(data.get(name, ""))

    def to_summary(self):
        self.fill_person()
        self.action("#participants-to-billing-button")
        self.step(4)
        self.fill_billing()
        self.action("#go-to-final-summary-button")
        self.step(5)

    def submit(self):
        self.action('#final-order-action-card button[type="submit"]')

    def assert_problem(self, name, step):
        self.step(step)
        field = self.page.locator(f'[name="{name}"]')
        expect(field).to_be_focused()
        expect(field).to_have_attribute("aria-invalid", "true")
        error_id = field.get_attribute("aria-describedby").split()[-1]
        expect(self.page.locator('[id="' + error_id + '"]')).to_be_visible()
        self.assertTrue(self.page.locator('[id="' + error_id + '"]').inner_text())

    def test_valid_single_desktop_and_mobile_orders(self):
        for width in (1366, 390):
            with self.subTest(width=width):
                if width == 390:
                    self.page.goto(self.live_server_url + reverse("register") + "?course=4")
                    self.page.evaluate("localStorage.clear()")
                    self.page.reload()
                    self.page.set_viewport_size({"width": width, "height": 844})
                    self.action("#go-to-participants-button")
                self.to_summary()
                self.page.locator("#terms-agreement").check()
                self.submit()
                self.page.wait_for_url("**/platba/*/")
                expect(self.page.get_by_role("link", name="Přeskočit odpočet a pokračovat")).to_be_visible()
                self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
        self.assertEqual(self.db(lambda: list(Order.objects.values_list("total_price", flat=True))), [990, 990])

    def test_invalid_inputs_focus_and_repair_at_each_step(self):
        self.fill_person()
        email = self.page.locator('[name="participants-0-email"]')
        for value in ("random", "jan@firma", "@example.cz", "   "):
            email.fill(value)
            self.action("#participants-to-billing-button")
            self.assert_problem("participants-0-email", 3)
        email.fill("valid@example.invalid")
        expect(email).not_to_have_attribute("aria-invalid", "true")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.fill_billing()
        for name, value in (("contact_phone", "text"), ("contact_email", "a@firma"),
                ("ico", "abcdef"), ("company_name", "   ")):
            original = self.page.locator(f'[name="{name}"]').input_value()
            self.page.locator(f'[name="{name}"]').fill(value)
            self.action("#go-to-final-summary-button")
            self.assert_problem(name, 4)
            self.page.locator(f'[name="{name}"]').fill(original)
        self.action("#go-to-final-summary-button")
        self.step(5)
        self.submit()
        self.assert_problem("terms_agreement", 5)
        self.page.locator("#terms-agreement").check()
        self.submit()
        self.page.wait_for_url("**/platba/*/")
        self.assertEqual(self.db(lambda: Order.objects.count()), 1)

    def test_mobile_errors_remain_visible_and_focusable(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.fill_person()
        self.page.locator('[name="participants-0-email"]').fill("broken")
        self.action("#participants-to-billing-button")
        self.assert_problem("participants-0-email", 3)
        self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
        self.page.locator('[name="participants-0-email"]').fill("fixed@example.invalid")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.fill_billing()
        self.page.locator('[name="contact_phone"]').fill("letters")
        self.action("#go-to-final-summary-button")
        self.assert_problem("contact_phone", 4)
        self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))

    def test_duplicate_emails_then_correction(self):
        self.fill_person()
        self.page.locator("#add-participant-button").click()
        self.fill_person(1)
        self.page.locator('[name="participants-1-email"]').fill("PERSON0@example.invalid")
        self.action("#participants-to-billing-button")
        self.assert_problem("participants-1-email", 3)
        self.page.locator('[name="participants-1-email"]').fill("other@example.invalid")
        self.action("#participants-to-billing-button")
        self.step(4)

    def test_final_submit_reveals_invalid_hidden_field_and_preserves_data(self):
        self.to_summary()
        self.page.locator("#terms-agreement").check()
        # Programmatic mutation represents a stale draft/autofill/other script.
        self.page.locator('[name="participants-0-email"]').evaluate("el => el.value = 'bad@'")
        self.submit()
        self.assert_problem("participants-0-email", 3)
        self.assertEqual(self.db(lambda: Order.objects.count()), 0)
        self.assertEqual(self.page.locator('[name="company_name"]').input_value(), "Testovací firma s.r.o.")
        self.page.locator('[name="participants-0-email"]').fill("fixed@example.invalid")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.action("#go-to-final-summary-button")
        self.step(5)
        self.page.locator('[name="contact_phone"]').evaluate("el => el.value = 'letters'")
        self.submit()
        self.assert_problem("contact_phone", 4)
        self.page.locator('[name="contact_phone"]').fill("777123456")
        self.action("#go-to-final-summary-button")
        self.step(5)
        self.submit()
        self.page.wait_for_url("**/platba/*/")

    def test_real_server_rejection_does_not_restore_stale_localstorage(self):
        self.to_summary()
        self.page.locator("#terms-agreement").check()
        self.page.evaluate("""() => {
            document.querySelector('[name=company_name]').value = 'SERVER zachovat';
            document.querySelector('[name=contact_phone]').value = 'not-a-phone';
            HTMLFormElement.prototype.submit.call(document.querySelector('#registration-form'));
        }""")
        expect(self.page.locator("#registration-form")).to_have_attribute("data-bound", "true")
        self.assert_problem("contact_phone", 4)
        expect(self.page.locator('[name="company_name"]')).to_have_value("SERVER zachovat")
        self.assertEqual(self.db(lambda: Order.objects.count()), 0)
        self.page.locator('[name="contact_phone"]').fill("777123456")
        self.action("#go-to-final-summary-button")
        self.step(5)
        self.submit()
        self.page.wait_for_url("**/platba/*/")
        self.assertEqual(self.db(lambda: Order.objects.get().company_name), "SERVER zachovat")

    def test_invalid_draft_reopens_correct_step_on_reload(self):
        self.to_summary()
        self.page.evaluate("""() => {
            const key = window.ElektroakademieOrderDraft.currentKey;
            const draft = JSON.parse(localStorage.getItem(key));
            draft.participants[0].email = 'restored@';
            draft.current_step = 5;
            localStorage.setItem(key, JSON.stringify(draft));
        }""")
        self.page.reload()
        self.assert_problem("participants-0-email", 3)
        expect(self.page.locator('[name="participants-0-email"]')).to_have_value("restored@")
        self.page.locator('[name="participants-0-email"]').fill("repaired@example.invalid")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.action("#go-to-final-summary-button")
        self.step(5)
        self.page.locator("#terms-agreement").check()
        self.submit()
        self.page.wait_for_url("**/platba/*/")

    def test_remove_middle_add_reload_and_group_price(self):
        for i, name in enumerate(("Anna", "Bob", "Cyril")):
            if i:
                self.page.locator("#add-participant-button").click()
            self.fill_person(i, name)
        self.page.locator(".remove-participant-button").nth(1).click()
        self.page.locator("#add-participant-button").click()
        self.fill_person(2, "David")
        # Row indices are reused after deletion; Cyril keeps person2, so the
        # new participant needs a different address despite having index 2.
        self.page.locator('[name="participants-2-email"]').fill("david@example.invalid")
        self.page.reload()
        self.step(3)
        expect(self.page.locator('[name="participants-1-first_name"]')).to_have_value("Cyril")
        expect(self.page.locator('#id_participants-TOTAL_FORMS')).to_have_value("3")
        emails = self.page.locator('#participants-wrapper input[name$="-email"]').evaluate_all(
            "inputs => inputs.map(input => input.value.toLowerCase())")
        self.assertEqual(len(emails), len(set(emails)), "Group fixture must use distinct emails")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.fill_billing()
        self.action("#go-to-final-summary-button")
        self.step(5)
        expect(self.page.locator("#final-participant-count")).to_have_text("3")
        self.page.locator("#terms-agreement").check()
        self.submit()
        self.page.wait_for_url("**/platba/*/")
        self.assertEqual(self.db(lambda: (Order.objects.get().total_price,
            list(OrderParticipant.objects.order_by("id").values_list("first_name", flat=True)))),
            (2970, ["Anna", "Cyril", "David"]))

    def test_ares_failure_manual_entry_and_country(self):
        self.fill_person()
        self.action("#participants-to-billing-button")
        self.step(4)
        self.page.route("**/api/ares/*/", lambda route: route.fulfill(status=503,
            content_type="application/json", body=json.dumps({"success": False, "message": "ARES nedostupný; vyplňte ručně."})))
        self.page.locator('[name="ico"]').fill("12345678")
        self.page.locator("#load-ares-button").click()
        expect(self.page.locator("#ares-status")).to_contain_text("ARES nedostupný")
        self.fill_billing()
        self.page.locator('[name="country"]').select_option("SK")
        self.action("#go-to-final-summary-button")
        self.step(5)
        expect(self.page.locator("#final-billing-summary")).to_contain_text("Slovensko")

    def test_global_form_and_formset_errors_are_visible(self):
        self.fill_person()
        self.page.locator('#id_participants-TOTAL_FORMS').evaluate("el => el.value = 'bad'")
        self.action("#participants-to-billing-button")
        self.step(3)
        expect(self.page.locator("#order-error-message")).to_be_visible()
        expect(self.page.locator("#order-error-message")).to_be_focused()
        self.page.locator('#id_participants-TOTAL_FORMS').evaluate("el => el.value = '1'")
        self.action("#participants-to-billing-button")
        self.step(4)
        self.fill_billing()
        from django.core.exceptions import ValidationError
        def invalid_clean(form):
            raise ValidationError("Test chyby celého fakturačního formuláře.")
        with patch.object(BillingForm, "clean", invalid_clean):
            self.action("#go-to-final-summary-button")
            expect(self.page.locator("#order-error-message")).to_contain_text("Test chyby celého")
            self.step(4)

    def test_validation_network_failure_is_actionable(self):
        self.fill_person()
        self.page.route("**/registrace/?*", lambda route: route.abort()
            if route.request.method == "POST" else route.continue_())
        self.action("#participants-to-billing-button")
        expect(self.page.locator("#order-error-message")).to_contain_text("Kontrolu objednávky nelze dokončit")
        expect(self.page.locator("#participants-to-billing-button")).to_be_enabled()
        self.step(3)
