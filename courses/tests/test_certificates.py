from datetime import datetime
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
    ParticipantProfile,
    QuizAttempt,
)
from courses.services import generate_certificate


User = get_user_model()


class CertificateTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jan.novak@example.com",
            email="jan.novak@example.com",
            password="Testheslo1",
            first_name="Jan",
            last_name="Novák",
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
            company_name="Testovací firma s.r.o.",
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
            email="jan.novak@example.com",
            registration_number="EA-04-202608-00001",
            activation_completed_at=timezone.now(),
        )

        self.profile = ParticipantProfile.objects.create(
            participant=self.participant,
            birth_date="1990-05-15",
            birth_place="Praha",
            permanent_address="Dlouhá 10, Praha",
            employer_name="Testovací firma s.r.o.",
            employer_address="Testovací 1, Praha",
        )

        self.submitted_at = timezone.make_aware(
            datetime(2026, 8, 7, 12, 0, 0)
        )

        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            total_questions=10,
            correct_answers=10,
            score_percent=100,
            passed=True,
            status=QuizAttempt.STATUS_SUBMITTED,
            submitted_at=self.submitted_at,
        )

        self.client.force_login(self.user)

    def create_certificate(self):
        certificate, created = generate_certificate(
            self.attempt
        )
        return certificate, created


class CertificateServiceTests(CertificateTestBase):
    def test_certificate_is_created_for_successful_attempt(self):
        certificate, created = self.create_certificate()

        self.assertTrue(created)
        self.assertEqual(
            Certificate.objects.count(),
            1,
        )

        self.assertEqual(
            certificate.participant,
            self.participant,
        )
        self.assertEqual(
            certificate.quiz_attempt,
            self.attempt,
        )

    def test_certificate_number_matches_registration_number(self):
        certificate, _ = self.create_certificate()

        self.assertEqual(
            certificate.certificate_number,
            "EA-04-202608-00001",
        )

        self.assertEqual(
            certificate.certificate_number,
            self.participant.registration_number,
        )

    def test_certificate_issued_at_matches_quiz_submission(self):
        certificate, _ = self.create_certificate()

        self.assertEqual(
            certificate.issued_at,
            self.submitted_at,
        )

    def test_certificate_validity_is_three_years_minus_one_day(self):
        certificate, _ = self.create_certificate()

        self.assertEqual(
            certificate.valid_until.isoformat(),
            "2029-08-06",
        )

    def test_certificate_generation_is_idempotent(self):
        first_certificate, first_created = (
            self.create_certificate()
        )

        second_certificate, second_created = (
            self.create_certificate()
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_certificate.pk,
            second_certificate.pk,
        )

        self.assertEqual(
            Certificate.objects.count(),
            1,
        )

    def test_in_progress_attempt_cannot_generate_certificate(self):
        self.attempt.status = (
            QuizAttempt.STATUS_IN_PROGRESS
        )
        self.attempt.save(
            update_fields=["status"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "Osvědčení lze vytvořit pouze pro odeslaný test.",
        ):
            generate_certificate(self.attempt)

        self.assertEqual(
            Certificate.objects.count(),
            0,
        )

    def test_failed_attempt_cannot_generate_certificate(self):
        self.attempt.passed = False
        self.attempt.save(
            update_fields=["passed"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "Osvědčení lze vytvořit pouze pro úspěšný test.",
        ):
            generate_certificate(self.attempt)

        self.assertEqual(
            Certificate.objects.count(),
            0,
        )

    def test_certificate_requires_participant_with_registration_number(
        self,
    ):
        self.participant.registration_number = None
        self.participant.save(
            update_fields=["registration_number"]
        )

        with self.assertRaisesMessage(
            ValueError,
            (
                "K uživateli nebyl nalezen aktivovaný účastník "
                "s evidenčním číslem."
            ),
        ):
            generate_certificate(self.attempt)

        self.assertEqual(
            Certificate.objects.count(),
            0,
        )


class CertificateViewTests(CertificateTestBase):
    def setUp(self):
        super().setUp()

        self.certificate, _ = self.create_certificate()

    def test_certificate_page_is_available_to_owner(self):
        response = self.client.get(
            reverse(
                "certificate_success",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "courses/certificate_success.html",
        )

        self.assertEqual(
            response.context["certificate"],
            self.certificate,
        )

        self.assertEqual(
            response.context["participant"],
            self.participant,
        )

    def test_unpaid_user_cannot_open_certificate_page(self):
        self.user.is_paid = False
        self.user.save(
            update_fields=["is_paid"]
        )

        response = self.client.get(
            reverse(
                "certificate_success",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "buy_course",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
        )

    def test_user_without_passed_quiz_cannot_open_certificate_page(
        self,
    ):
        self.user.passed_quiz = False
        self.user.save(
            update_fields=["passed_quiz"]
        )

        response = self.client.get(
            reverse(
                "certificate_success",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
        )

    def test_user_cannot_open_another_users_certificate(self):
        other_user = User.objects.create_user(
            username="petr@example.com",
            email="petr@example.com",
            password="Testheslo1",
            is_paid=True,
            passed_quiz=True,
        )

        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                "certificate_success",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    @patch(
        "courses.views.generate_certificate_pdf",
        return_value=b"%PDF-test-content",
    )
    def test_certificate_pdf_is_returned_for_owner(
        self,
        mock_generate_pdf,
    ):
        response = self.client.get(
            reverse(
                "certificate_pdf",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )

        self.assertEqual(
            response.content,
            b"%PDF-test-content",
        )

        self.assertEqual(
            response["Content-Disposition"],
            (
                'inline; filename="'
                'EA-04-202608-00001.pdf"'
            ),
        )

        mock_generate_pdf.assert_called_once_with(
            self.certificate
        )

    @patch(
        "courses.views.generate_certificate_pdf",
        return_value=b"%PDF-test-content",
    )
    def test_user_cannot_download_another_users_certificate(
        self,
        mock_generate_pdf,
    ):
        other_user = User.objects.create_user(
            username="petr@example.com",
            email="petr@example.com",
            password="Testheslo1",
            is_paid=True,
            passed_quiz=True,
        )

        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                "certificate_pdf",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        mock_generate_pdf.assert_not_called()