import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class LegalDocumentPresentationTests(TestCase):
    def _static_source(self, relative_path):
        return (
            Path(settings.BASE_DIR)
            / "courses"
            / "static"
            / "courses"
            / relative_path
        ).read_text(encoding="utf-8")

    def test_legal_document_urls_render_expected_templates(self):
        cases = (
            (
                "terms_and_conditions",
                "/obchodni-podminky/",
                "courses/terms_and_conditions.html",
            ),
            (
                "privacy_policy",
                "/zasady-ochrany-osobnich-udaju/",
                "courses/privacy_policy.html",
            ),
        )

        for url_name, expected_path, template_name in cases:
            with self.subTest(url_name=url_name):
                self.assertEqual(reverse(url_name), expected_path)
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template_name)

    def test_registration_modal_iframes_keep_legal_urls(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'src="{reverse("terms_and_conditions")}" title="Obchodní podmínky"',
        )
        self.assertContains(
            response,
            f'src="{reverse("privacy_policy")}" title="Zásady ochrany osobních údajů"',
        )

    def test_legal_pages_remove_normal_header_controls_and_center_logo(self):
        for url_name in ("terms_and_conditions", "privacy_policy"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                content = response.content.decode("utf-8")

                self.assertIn('class="topbar legal-topbar"', content)
                self.assertIn('class="logo" id="home-link"', content)
                self.assertNotIn("Přihlásit se", content)
                self.assertNotIn("Mám zájem", content)
                self.assertNotIn("Rozpracovaná objednávka", content)
                self.assertNotIn('id="mobile-menu-toggle"', content)
                self.assertNotIn('id="top-navigation"', content)

        css = self._static_source(Path("css") / "terms.css")
        self.assertRegex(
            css,
            r"\.legal-topbar\s+\.topbar-inner\s*\{[^}]*justify-content:\s*center;",
        )

    def test_normal_and_registration_headers_keep_their_current_actions(self):
        index_response = self.client.get(reverse("index"))
        self.assertContains(index_response, "Přihlásit se")
        self.assertContains(index_response, "Mám zájem")
        self.assertContains(index_response, "Rozpracovaná objednávka")
        self.assertContains(index_response, 'id="start-order-link"')
        self.assertContains(index_response, 'id="draft-order-link"')

        register_response = self.client.get(reverse("register"))
        register_content = register_response.content.decode("utf-8")
        self.assertIn("Návrat na domovskou stránku", register_content)
        self.assertNotIn('id="start-order-link"', register_content)
        self.assertNotIn('id="draft-order-link"', register_content)

    def test_legal_numbering_uses_same_color_as_section_headings(self):
        css = self._static_source(Path("css") / "terms.css")

        h2_rule = re.search(r"\.terms-card h2\s*\{(?P<body>[^}]*)\}", css, re.S)
        h3_rule = re.search(r"\.terms-card h3\s*\{(?P<body>[^}]*)\}", css, re.S)
        self.assertIsNotNone(h2_rule)
        self.assertIsNotNone(h3_rule)

        h2_color = re.search(r"color:\s*([^;]+);", h2_rule.group("body")).group(1).strip()
        h3_color = re.search(r"color:\s*([^;]+);", h3_rule.group("body")).group(1).strip()

        self.assertEqual(h2_color, "var(--color-bg-mid)")
        self.assertEqual(h3_color, h2_color)

    def test_registration_javascript_contains_no_django_template_tags(self):
        source = self._static_source(Path("js") / "registration.js")
        self.assertNotIn("{%", source)
        self.assertNotIn("{{", source)
