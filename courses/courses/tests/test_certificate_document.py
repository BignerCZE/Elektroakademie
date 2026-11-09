from unittest.mock import patch

from django.urls import reverse

from courses.services import generate_certificate_pdf, load_static_data_uri
from courses.tests.test_certificates import CertificateTestBase


class CertificateDocumentTests(CertificateTestBase):
    def render_document(self):
        certificate, _ = self.create_certificate()
        with patch("courses.services.generate_html_pdf", return_value=b"%PDF-test") as render:
            self.assertEqual(generate_certificate_pdf(certificate), b"%PDF-test")
        return render.call_args.args[0]

    def test_pdf_embeds_logo_without_slogan(self):
        with patch("courses.services.load_static_data_uri", wraps=load_static_data_uri) as assets:
            self.render_document()
        assets.assert_any_call("courses/img/svetle_pozadi_bez_sloganu.svg", "image/svg+xml")
        self.assertNotIn(
            ("courses/img/cz_svetle_pozadi.svg", "image/svg+xml"),
            [call.args for call in assets.call_args_list],
        )

    def test_document_uses_participant_data_and_escapes_user_content(self):
        self.profile.employer_ico = "00123456"
        self.profile.employer_name = 'Firma <panelu> & zařízení'
        self.profile.activity_scope = "Tento rozsah se nesmí vytisknout"
        self.profile.workplace_specification = "Výrobní hala č. 2"
        self.profile.save()
        html = self.render_document()
        for value in (
            "00123456", "Firma &lt;panelu&gt; &amp; zařízení",
            "EA-04-202608-00001", "Jan Novák",
            "7. 8. 2026", "6. 8. 2029", "data:image/svg+xml;base64,",
            "data:image/png;base64,", "Pracovní a technologické postupy",
            "byla prakticky zacvičena", "samostatně vyplnila test",
            "a osobou odpovědnou za zaměstnavatele.",
        ):
            with self.subTest(value=value):
                self.assertIn(value, html)
        self.assertNotIn("Tento rozsah se nesmí vytisknout", html)
        self.assertNotIn("Výrobní hala č. 2", html)
        self.assertEqual(html.count('class="certificate-writing-line"'), 4)
        self.assertNotIn('src="/static/', html)
        self.assertNotIn("VYPÍŠE ZAMĚSTNANEC", html)

    def test_legacy_profile_does_not_use_billing_ico_as_employer_ico(self):
        self.order.ico = "87654321"
        self.order.save()
        html = self.render_document()
        self.assertNotIn("87654321", html)
        self.assertIn("Neuvedeno", html)

    def test_pdf_can_be_generated_without_profile(self):
        self.profile.delete()
        self.assertIn("Neuvedeno", self.render_document())

    def test_dashboard_pdf_link_uses_existing_download_endpoint(self):
        self.create_certificate()
        response = self.client.get(reverse("certificate_success", args=[self.course.pk]))
        self.assertContains(response, reverse("certificate_pdf", args=[self.course.pk]))
