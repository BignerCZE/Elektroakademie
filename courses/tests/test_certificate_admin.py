from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import (
    Certificate,
    Course,
    Order,
    OrderParticipant,
    QuizAttempt,
)


User = get_user_model()


class CertificateAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="certificate-admin@example.com",
            email="certificate-admin@example.com",
            password="Testheslo1",
        )
        self.user = User.objects.create_user(
            username="participant@example.com",
            email="participant@example.com",
            first_name="Jan",
            last_name="Novák",
            password="Testheslo1",
            is_paid=True,
            passed_quiz=True,
        )
        self.course = Course.objects.create(
            title="§4 – osoba poučená",
            description="Testovací kurz",
            video_url="https://example.com/video",
        )
        self.order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Test s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="Česká republika",
        )
        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email="participant@example.com",
            registration_number="EA-04-202608-00001",
            activation_completed_at=timezone.now(),
        )
        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=10,
            correct_answers=9,
            score_percent=90,
            passed=True,
            submitted_at=timezone.now(),
        )
        self.certificate = Certificate.objects.create(
            participant=self.participant,
            quiz_attempt=self.attempt,
            certificate_number="EA-04-202608-00001",
            issued_at=timezone.now(),
            valid_until=(
                timezone.localdate()
                + timedelta(days=365)
            ),
        )

        self.client.force_login(self.superuser)

    def test_certificate_change_view_contains_work_dashboard(self):
        response = self.client.get(
            reverse(
                "admin:courses_certificate_change",
                args=[self.certificate.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "certificate-dashboard")
        self.assertContains(
            response,
            self.certificate.certificate_number,
        )
        self.assertContains(response, "Otevřít účastníka")
        self.assertContains(response, "Otevřít testový pokus")
        self.assertContains(response, "Otevřít PDF")

    def test_certificate_changelist_shows_validity_and_pdf(self):
        response = self.client.get(
            reverse(
                "admin:courses_certificate_changelist"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.certificate.certificate_number,
        )
        self.assertContains(response, "Platný")
        self.assertContains(response, ">PDF<", html=False)

    def test_expired_certificate_is_marked_invalid(self):
        self.certificate.valid_until = (
            timezone.localdate()
            - timedelta(days=1)
        )
        self.certificate.save(
            update_fields=["valid_until"]
        )

        response = self.client.get(
            reverse(
                "admin:courses_certificate_change",
                args=[self.certificate.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Neplatný")
        self.assertContains(
            response,
            "Platnost skončila před 1 dny.",
        )

    def test_expiring_filter_returns_certificate(self):
        self.certificate.valid_until = (
            timezone.localdate()
            + timedelta(days=30)
        )
        self.certificate.save(
            update_fields=["valid_until"]
        )

        response = self.client.get(
            reverse(
                "admin:courses_certificate_changelist"
            ),
            {"validity": "expiring"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.certificate.certificate_number,
        )

    @patch(
        "courses.admin.generate_certificate_pdf",
        return_value=b"%PDF-test",
    )
    def test_admin_pdf_endpoint_is_staff_only_and_returns_pdf(
        self,
        generate_certificate_pdf_mock,
    ):
        response = self.client.get(
            reverse(
                "admin:courses_certificate_pdf",
                args=[self.certificate.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )
        self.assertIn(
            "inline;",
            response["Content-Disposition"],
        )
        self.assertEqual(response.content, b"%PDF-test")
        generate_certificate_pdf_mock.assert_called_once()

    def test_admin_pdf_endpoint_redirects_anonymous_user(self):
        self.client.logout()

        response = self.client.get(
            reverse(
                "admin:courses_certificate_pdf",
                args=[self.certificate.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("admin:login"),
            response.url,
        )
