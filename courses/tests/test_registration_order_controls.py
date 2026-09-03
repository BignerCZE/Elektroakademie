from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from courses.models import Order, OrderParticipant


class RegistrationOrderControlsTests(TestCase):
    def get_registration_data(self, selected_course="4"):
        return {
            "selected_course": selected_course,
            "participants-TOTAL_FORMS": "1",
            "participants-INITIAL_FORMS": "0",
            "participants-MIN_NUM_FORMS": "1",
            "participants-MAX_NUM_FORMS": "1000",
            "participants-0-first_name": "Jan",
            "participants-0-last_name": "Novák",
            "participants-0-email": "jan.novak@example.com",
            "ico": "12345678",
            "dic": "CZ12345678",
            "company_name": "Testovací firma s.r.o.",
            "street": "Testovací 1",
            "city": "Praha",
            "zip_code": "11000",
            "country": "CZ",
            "contact_first_name": "Petr",
            "contact_last_name": "Svoboda",
            "contact_phone_prefix": "+420",
            "contact_phone": "777 123 456",
            "contact_email": "kontakt@example.com",
            "note": "Testovací objednávka",
        }

    def test_registration_page_keeps_external_assets_and_contact_url(self):
        response = self.client.get(reverse("register"))
        contact_url = f'{reverse("index")}#contact'

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'courses/css/course-selector.css?v=4',
        )
        self.assertContains(
            response,
            'courses/css/registration.css?v=3',
        )
        self.assertContains(
            response,
            'courses/js/registration.js?v=3',
        )
        self.assertContains(
            response,
            f'data-check-emails-url="{reverse("check_participant_emails")}"',
        )
        self.assertContains(
            response,
            f'data-index-url="{reverse("index")}"',
        )
        self.assertContains(
            response,
            f'data-contact-url="{contact_url}"',
        )
        self.assertContains(
            response,
            f'href="{contact_url}" class="selector-card selector-card--link"',
        )

    def test_registration_header_has_only_home_return_action(self):
        response = self.client.get(reverse("register"))
        content = response.content.decode("utf-8")

        self.assertIn("Návrat na domovskou stránku", content)
        self.assertNotIn('id="start-order-link"', content)
        self.assertNotIn('id="draft-order-link"', content)
        self.assertNotIn('href="' + reverse("login") + '" class="login-link"', content)

    def test_summary_uses_sticky_side_action_and_has_no_inline_back_button(self):
        response = self.client.get(reverse("register"))
        content = response.content.decode("utf-8")

        self.assertIn('data-step-panel="5"', content)
        self.assertIn('id="final-order-action-card"', content)
        self.assertIn('form="registration-form"', content)
        self.assertIn("Dokončit objednávku", content)
        self.assertIn('class="terms-agreement-label final-action-consent"', content)
        self.assertIn('name="terms_agreement" form="registration-form" required', content)
        final_panel_start = content.index('id="final-order-action-card"')
        consent_position = content.index('id="terms-agreement"', final_panel_start)
        submit_position = content.index('type="submit"', final_panel_start)
        self.assertLess(consent_position, submit_position)
        self.assertNotIn('id="summary-previous-button"', content)

    def test_checkout_has_no_delete_order_controls(self):
        response = self.client.get(reverse("register"))
        content = response.content.decode("utf-8")

        self.assertNotIn("Zrušit objednávku", content)
        self.assertNotIn("delete-order-button", content)
        self.assertEqual(content.count('class="restart-order-button"'), 3)
        self.assertEqual(content.count("Návrat na začátek objednávky"), 3)

    def test_contact_only_courses_cannot_create_standard_order(self):
        for course_id in ("6", "7"):
            with self.subTest(course_id=course_id):
                response = self.client.post(
                    reverse("register"),
                    self.get_registration_data(selected_course=course_id),
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(Order.objects.count(), 0)
                self.assertEqual(OrderParticipant.objects.count(), 0)

    def test_registration_javascript_has_expected_course_routing(self):
        source = self._read_static("js", "registration.js")

        self.assertIn('orderMode: "standard"', source)
        self.assertEqual(source.count('orderMode: "contact"'), 2)
        self.assertIn(
            "Toto školení aktuálně probíhá individuální formou.",
            source,
        )
        self.assertIn("Přejít na kontaktní formulář", source)
        self.assertIn(
            "window.location.href = registrationForm.dataset.contactUrl;",
            source,
        )
        self.assertIn(
            "if (isContactCourse(courseId) && step >= 3)",
            source,
        )
        self.assertIn(
            "if (!isStandardOrderCourse(courseId))",
            source,
        )
        self.assertIn(
            "draft && draft.selected_course === selectedCourseId",
            source,
        )

    def test_restart_buttons_share_one_non_destructive_handler(self):
        source = self._read_static("js", "registration.js")

        self.assertEqual(
            source.count('document.querySelectorAll(".restart-order-button")'),
            1,
        )
        self.assertEqual(
            source.count('addEventListener("click", returnToOrderStart)'),
            1,
        )
        self.assertEqual(source.count("function returnToOrderStart()"), 1)
        self.assertNotIn("function deleteDraftOrder()", source)
        self.assertNotIn("orderDraftStorage.clear();", source)

        handler_start = source.index("function returnToOrderStart()")
        handler_end = source.index(
            'document.querySelectorAll(".restart-order-button")',
            handler_start,
        )
        handler = source[handler_start:handler_end]

        self.assertIn("showStep(1);", handler)
        self.assertIn("saveOrderDraft();", handler)
        self.assertLess(handler.index("showStep(1);"), handler.index("saveOrderDraft();"))

    def test_registration_javascript_contains_no_django_template_tags(self):
        source = self._read_static("js", "registration.js")

        self.assertNotIn("{%", source)
        self.assertNotIn("{{", source)

    def test_order_button_styles_and_sticky_panels_cover_required_states(self):
        source = self._read_static("css", "registration.css")

        self.assertIn(".register-page .summary-submit-button", source)
        self.assertIn(".register-page .restart-order-button:hover:not(:disabled)", source)
        self.assertIn(".register-page .restart-order-button:focus-visible", source)
        self.assertIn(":active:not(:disabled)", source)
        self.assertIn(".register-page .restart-order-button:disabled", source)
        self.assertIn("top: calc(var(--header-height) + 104px);", source)
        self.assertIn(".register-page .final-order-action-card", source)
        self.assertIn("@media (max-width: 1100px)", source)

    def _read_static(self, kind, filename):
        path = (
            Path(settings.BASE_DIR)
            / "courses"
            / "static"
            / "courses"
            / kind
            / filename
        )
        return path.read_text(encoding="utf-8")
