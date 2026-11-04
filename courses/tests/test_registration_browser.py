"""Browser regression: deleting rows must preserve every displayed participant.

Run with Playwright Chromium installed (python -m playwright install chromium).
"""
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright, Error

from courses.models import Order


@override_settings(EMAIL_TRANSPORT="preview", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ParticipantRemovalBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.launch()
        except Error as error:
            self.playwright.stop()
            if "Executable doesn't exist" in str(error):
                self.skipTest("Install Playwright Chromium for browser regression checks.")
            raise
        self.context = self.browser.new_context(viewport={"width":1366,"height":900})
        self.context.route("**/*", lambda route: route.continue_()
                           if route.request.url.startswith(self.live_server_url) else route.abort())
        self.page = self.context.new_page()
        self.page.goto(self.live_server_url + "/registrace/?course=4")
        self.page.locator('[data-cookie-choice="none"]').click()
        self.page.locator('#go-to-participants-button').click()

    def tearDown(self):
        if hasattr(self,"browser"):
            self.browser.close()
            self.playwright.stop()
        super().tearDown()

    def fill_person(self, index, name):
        for field,value in [("first_name",name),("last_name","Test"),("email",name.lower()+"@example.invalid")]:
            self.page.locator(f'[name="participants-{index}-{field}"]').fill(value)

    def assert_indices(self, count):
        self.assertEqual(self.page.locator('#id_participants-TOTAL_FORMS').input_value(),str(count))
        names=self.page.locator('#participants-wrapper input[name]').evaluate_all('(els)=>els.map(e=>e.name)')
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(set(names),{f"participants-{i}-{field}" for i in range(count)
                                    for field in ["first_name","last_name","email"]})
        ids=self.page.locator('#participants-wrapper [id]').evaluate_all('(els)=>els.map(e=>e.id)')
        self.assertEqual(len(ids),len(set(ids)))

    def test_remove_middle_readd_restore_and_submit_keeps_all_people(self):
        for index,name in enumerate(["Alice","Bob","Carol"]):
            if index:self.page.locator('#add-participant-button').click()
            self.fill_person(index,name)
        self.page.locator('.remove-participant-button').nth(1).click()
        self.assert_indices(2)
        self.assertEqual(self.page.locator('[name="participants-1-first_name"]').input_value(),"Carol")
        self.page.locator('#add-participant-button').click()
        self.fill_person(2,"David")
        self.assert_indices(3)
        self.page.goto(self.live_server_url + '/registrace/')
        self.assert_indices(3)
        self.assertEqual(self.page.locator('[name="participants-1-first_name"]').input_value(),"Carol")
        self.page.locator('#participants-to-billing-button').click()
        for name,value in {"company_name":"Test Ltd","street":"Test 1","city":"Ostrava","zip_code":"70030",
                           "contact_first_name":"Test","contact_last_name":"Contact","contact_phone_prefix":"+420",
                           "contact_phone":"123456789","contact_email":"contact@example.invalid"}.items():
            self.page.locator(f'[name="{name}"]').fill(value)
        self.page.locator('#go-to-final-summary-button').click()
        self.page.locator('#terms-agreement').check()
        self.page.locator('#final-order-action-card button[type=submit]').click()
        self.page.wait_for_url('**/platba/*/')
        def saved_order():
            # Playwright sync keeps an event loop on this thread. Use a separate
            # DB thread, not DJANGO_ALLOW_ASYNC_UNSAFE, to inspect server data.
            close_old_connections()
            try:
                order = Order.objects.get()
                return order.total_price, list(order.participants.order_by("id").values_list("first_name", flat=True))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            price, names = pool.submit(saved_order).result(timeout=5)
        self.assertEqual(price,2970)
        self.assertEqual(names,["Alice","Carol","David"])

    def test_remove_first_and_last_keep_contiguous_indices(self):
        for _ in range(2):self.page.locator('#add-participant-button').click()
        self.page.locator('.remove-participant-button').first.click()
        self.assert_indices(2)
        self.page.locator('.remove-participant-button').last.click()
        self.assert_indices(1)
        self.assertFalse(self.page.locator('.remove-participant-button').first.is_visible())
