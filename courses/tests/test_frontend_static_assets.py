from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from courses.models import Order


class FrontendStaticAssetTests(TestCase):
    expected_assets = (
        "courses/css/registration.css",
        "courses/css/certificate-print.css",
        "courses/js/order-draft-storage.js",
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

    def test_base_loads_shared_draft_storage_before_dependent_scripts(self):
        response = self.client.get(reverse("register"))
        content = response.content.decode()

        storage_asset = "/static/courses/js/order-draft-storage.js?v=1"
        base_asset = "/static/courses/js/base.js?v=2"
        registration_asset = "/static/courses/js/registration.js?v=1"

        self.assertContains(response, storage_asset)
        self.assertLess(content.index(storage_asset), content.index(base_asset))
        self.assertLess(content.index(storage_asset), content.index(registration_asset))

    def test_failed_registration_does_not_load_draft_cleanup_script(self):
        response = self.client.post(reverse("register"), {})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")
        self.assertNotContains(
            response,
            "/static/courses/js/payment-simulation.js?v=2",
        )
        self.assertNotContains(
            response,
            "/static/courses/js/payment-success.js?v=2",
        )

    def test_payment_pages_load_draft_cleanup_mechanism(self):
        simulation_source = self._template_source(
            "registration/payment_simulation.html"
        )
        success_source = self._template_source(
            "registration/order_payment_success.html"
        )

        self.assertIn("courses/js/payment-simulation.js", simulation_source)
        self.assertIn("courses/js/payment-success.js", success_source)
        self.assertIn(
            "ElektroakademieOrderDraft.clear()",
            self._static_source("courses/js/payment-simulation.js"),
        )
        self.assertIn(
            "ElektroakademieOrderDraft.clear()",
            self._static_source("courses/js/payment-success.js"),
        )

    def test_payment_simulation_keeps_success_url_in_data_attribute(self):
        order = Order.objects.create(
            course_type="4",
            total_price=990,
            company_name="Testovací objednatel",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
        )

        response = self.client.get(
            reverse("order_payment_simulation", args=[order.id])
        )

        self.assertContains(
            response,
            (
                'data-success-url="'
                f'{reverse("order_payment_success", args=[order.id])}"'
            ),
        )
        self.assertContains(
            response,
            "/static/courses/js/payment-simulation.js?v=2",
        )

    def test_shared_draft_storage_supports_all_known_keys(self):
        source = self._static_source("courses/js/order-draft-storage.js")

        for key in (
            "elektroakademie_order_draft",
            "elektroakademie_order_draft_v2",
            "elektroakademie_order_draft_v3",
        ):
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', source)

        self.assertIn("localStorage.removeItem(key)", source)
        self.assertIn("localStorage.getItem(key)", source)
        self.assertIn(
            "ElektroakademieOrderDraft.exists()",
            self._static_source("courses/js/base.js"),
        )

    def test_active_javascript_has_no_django_template_tags(self):
        for asset in self.expected_assets:
            if not asset.endswith(".js"):
                continue

            with self.subTest(asset=asset):
                source = self._static_source(asset)
                self.assertNotIn("{%", source)
                self.assertNotIn("{{", source)

    @staticmethod
    def _template_source(relative_path):
        template_root = Path(settings.BASE_DIR) / "courses" / "templates"
        return (template_root / relative_path).read_text(encoding="utf-8")

    @staticmethod
    def _static_source(relative_path):
        static_root = Path(settings.BASE_DIR) / "courses" / "static"
        return (static_root / relative_path).read_text(encoding="utf-8")

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
