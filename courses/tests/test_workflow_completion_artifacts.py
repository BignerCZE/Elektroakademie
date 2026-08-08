from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from courses.models import (
    Course,
    EmailLog,
    Order,
    OrderParticipant,
    QuizAttempt,
)
from courses.workflows import process_quiz_completion


User = get_user_model()


@override_settings(
    EMAIL_TRANSPORT="preview",
    SITE_URL="http://testserver",
)
class QuizCompletionArtifactWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="artifact@example.com",
            email="artifact@example.com",
            first_name="Jan",
            last_name="Novák",
            password="Testheslo1",
            is_paid=True,
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
            paid_at=timezone.now(),
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
            contact_email="kontakt@example.com",
        )
        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email=self.user.email,
            registration_number="EA-04-202608-00002",
            activation_completed_at=timezone.now(),
        )
        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=10,
            correct_answers=8,
            score_percent=80,
            passed=True,
            submitted_at=timezone.now(),
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf",
        return_value=b"%PDF quiz",
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_success_generates_both_artifacts_and_preview_log(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        result = process_quiz_completion(
            self.attempt
        )

        self.assertEqual(result.errors, ())
        mock_certificate_pdf.assert_called_once()
        mock_quiz_pdf.assert_called_once_with(
            self.attempt
        )

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=self.attempt,
        )
        self.assertEqual(
            log.status,
            EmailLog.STATUS_PREVIEW,
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf"
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        side_effect=RuntimeError(
            "Chromium není dostupný"
        ),
    )
    def test_certificate_pdf_failure_is_logged(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        result = process_quiz_completion(
            self.attempt
        )

        self.assertTrue(result.errors)
        mock_certificate_pdf.assert_called_once()
        mock_quiz_pdf.assert_not_called()

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=self.attempt,
        )
        self.assertEqual(
            log.status,
            EmailLog.STATUS_FAILED,
        )
        self.assertIn(
            "Chromium není dostupný",
            log.error_message,
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf",
        side_effect=RuntimeError(
            "ReportLab chyba"
        ),
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_quiz_pdf_failure_is_logged(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        result = process_quiz_completion(
            self.attempt
        )

        self.assertTrue(result.errors)
        mock_certificate_pdf.assert_called_once()
        mock_quiz_pdf.assert_called_once_with(
            self.attempt
        )

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=self.attempt,
        )
        self.assertEqual(
            log.status,
            EmailLog.STATUS_FAILED,
        )
        self.assertIn(
            "ReportLab chyba",
            log.error_message,
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf",
        return_value=b"%PDF quiz",
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        return_value=b"not-a-pdf",
    )
    def test_invalid_pdf_content_is_logged_as_failure(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        result = process_quiz_completion(
            self.attempt
        )

        self.assertTrue(result.errors)
        mock_quiz_pdf.assert_not_called()

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=self.attempt,
        )
        self.assertEqual(
            log.status,
            EmailLog.STATUS_FAILED,
        )
        self.assertIn(
            "platnou PDF hlavičku",
            log.error_message,
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf",
        return_value=b"%PDF quiz",
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        side_effect=[
            RuntimeError("Dočasná chyba"),
            b"%PDF certificate",
        ],
    )
    def test_failed_artifact_generation_can_be_retried(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        first_result = process_quiz_completion(
            self.attempt
        )
        second_result = process_quiz_completion(
            self.attempt
        )

        self.assertTrue(first_result.errors)
        self.assertEqual(second_result.errors, ())
        self.assertEqual(
            mock_certificate_pdf.call_count,
            2,
        )
        mock_quiz_pdf.assert_called_once_with(
            self.attempt
        )

        logs = EmailLog.objects.filter(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=self.attempt,
        )
        self.assertEqual(
            logs.filter(
                status=EmailLog.STATUS_FAILED,
            ).count(),
            1,
        )
        self.assertEqual(
            logs.filter(
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            1,
        )

    @patch(
        "courses.workflows.generate_quiz_result_pdf",
        return_value=b"%PDF quiz",
    )
    @patch(
        "courses.workflows.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_completed_preview_does_not_regenerate_artifacts(
        self,
        mock_certificate_pdf,
        mock_quiz_pdf,
    ):
        process_quiz_completion(
            self.attempt
        )
        process_quiz_completion(
            self.attempt
        )

        mock_certificate_pdf.assert_called_once()
        mock_quiz_pdf.assert_called_once()

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=EmailLog.TYPE_COURSE_COMPLETED,
                quiz_attempt=self.attempt,
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            1,
        )
