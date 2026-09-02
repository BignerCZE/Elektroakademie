from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class FrontendStaticAssetTests(TestCase):
    expected_assets = (
        "courses/css/registration.css",
        "courses/css/certificate-print.css",
        "courses/js/base.js",
        "courses/js/landing.js",
        "courses/js/registration.js",
        "courses/js/quiz-question.js",
        "courses/js/certificate-preview.js",
        "courses/js/payment-simulation.js",
        "courses/js/payment-success.js",
    )

    def test_refactored_static_assets_are_discoverable(self):
        for asset in self.expected_assets:
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

    def test_index_loads_assets_and_keeps_contact_and_faq(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, "/static/courses/css/landing.css?v=20")
        self.assertContains(response, "/static/courses/js/landing.js?v=1")
        self.assertContains(response, 'id="contact"')
        self.assertContains(response, 'id="faq"')
        self.assertContains(response, 'class="faq-list"')
        self.assertContains(response, "Často kladené otázky")

    def test_registration_loads_assets_and_exposes_backend_urls(self):
        response = self.client.get(reverse("register"))

        self.assertContains(response, "/static/courses/css/registration.css?v=1")
        self.assertContains(response, "/static/courses/js/registration.js?v=1")
        self.assertContains(
            response,
            f'data-check-emails-url="{reverse("check_participant_emails")}"',
        )
        self.assertContains(response, f'data-index-url="{reverse("index")}"')

    def test_active_application_templates_have_no_inline_blocks(self):
        template_root = Path(settings.BASE_DIR) / "courses" / "templates"
        active_templates = (
            "courses/base.html",
            "courses/index.html",
            "courses/certificate_print.html",
            "courses/certificate_success.html",
            "courses/quiz_question.html",
            "registration/register.html",
            "registration/payment_simulation.html",
            "registration/order_payment_success.html",
        )

        for relative_path in active_templates:
            with self.subTest(template=relative_path):
                source = (template_root / relative_path).read_text(encoding="utf-8")
                self.assertNotIn("<style>", source)
                self.assertNotIn("<script>", source)
