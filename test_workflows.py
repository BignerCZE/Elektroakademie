from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from courses.emails.types import RenderedEmail
from courses.models import (
    Certificate,
    Course,
    EmailLog,
    Order,
    OrderParticipant,
    QuizAttempt,
)
from courses.workflows import (
    process_order_payment,
    process_quiz_completion,
)


User = get_user_model()


@override_settings(
    EMAIL_TRANSPORT="preview",
    SITE_URL="http://testserver",
)
class OrderPaymentWorkflowTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=1980,
            status="pending_payment",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
            contact_first_name="Petr",
            contact_last_name="Svoboda",
            contact_email="kontakt@example.com",
        )
        self.participant_1 = OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
        )
        self.participant_2 = OrderParticipant.objects.create(
            order=self.order,
            first_name="Eva",
            last_name="Nováková",
            email="eva@example.com",
        )

    def test_payment_workflow_completes_whole_preview_flow(self):
        result = process_order_payment(
            self.order.pk
        )

        self.order.refresh_from_db()
        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        self.assertTrue(result.status_changed)
        self.assertEqual(self.order.status, "paid")
        self.assertIsNotNone(self.order.paid_at)
        self.assertTrue(
            self.participant_1.registration_number
        )
        self.assertTrue(
            self.participant_2.registration_number
        )
        self.assertEqual(
            EmailLog.objects.filter(
                order=self.order,
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            3,
        )

    def test_payment_workflow_is_idempotent(self):
        process_order_payment(self.order.pk)
        original_paid_at = (
            Order.objects.get(pk=self.order.pk).paid_at
        )

        result = process_order_payment(
            self.order.pk
        )

        self.order.refresh_from_db()

        self.assertFalse(result.status_changed)
        self.assertEqual(
            self.order.paid_at,
            original_paid_at,
        )
        self.assertEqual(
            EmailLog.objects.filter(
                order=self.order,
            ).count(),
            3,
        )

    def test_already_paid_order_with_missing_logs_is_reconciled(self):
        self.order.status = "paid"
        self.order.paid_at = timezone.now()
        self.order.save(
            update_fields=["status", "paid_at"]
        )

        result = process_order_payment(
            self.order.pk
        )

        self.assertFalse(result.status_changed)
        self.assertEqual(
            EmailLog.objects.filter(
                order=self.order,
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            3,
        )


@override_settings(
    EMAIL_TRANSPORT="preview",
    SITE_URL="http://testserver",
)
class QuizCompletionWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jan@example.com",
            email="jan@example.com",
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
            email="jan@example.com",
            registration_number="EA-04-202608-00001",
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

    def _rendered_email(self):
        return RenderedEmail(
            subject="Dokončení kurzu",
            recipient=self.user.email,
            text_body="Text",
            html_body="<p>HTML</p>",
        )

    @patch(
        "courses.workflows.build_course_completed_email"
    )
    def test_quiz_workflow_creates_certificate_and_email_log(
        self,
        mock_builder,
    ):
        mock_builder.return_value = self._rendered_email()

        result = process_quiz_completion(
            self.attempt
        )

        self.assertTrue(result.certificate_created)
        self.assertTrue(
            Certificate.objects.filter(
                quiz_attempt=self.attempt,
            ).exists()
        )
        self.assertEqual(
            EmailLog.objects.filter(
                email_type=EmailLog.TYPE_COURSE_COMPLETED,
                quiz_attempt=self.attempt,
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            1,
        )

    @patch(
        "courses.workflows.build_course_completed_email"
    )
    def test_quiz_workflow_does_not_duplicate_completed_email(
        self,
        mock_builder,
    ):
        mock_builder.return_value = self._rendered_email()

        process_quiz_completion(self.attempt)
        process_quiz_completion(self.attempt)

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=EmailLog.TYPE_COURSE_COMPLETED,
                quiz_attempt=self.attempt,
            ).count(),
            1,
        )

    @patch(
        "courses.workflows.build_course_completed_email"
    )
    def test_failed_log_does_not_block_retry(
        self,
        mock_builder,
    ):
        mock_builder.return_value = self._rendered_email()

        Certificate.objects.create(
            participant=self.participant,
            quiz_attempt=self.attempt,
            certificate_number=(
                self.participant.registration_number
            ),
            issued_at=self.attempt.submitted_at,
            valid_until=timezone.localdate(),
        )
        EmailLog.objects.create(
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            recipient=self.user.email,
            subject="Předchozí pokus",
            status=EmailLog.STATUS_FAILED,
            error_message="Testovací chyba",
            quiz_attempt=self.attempt,
        )

        process_quiz_completion(self.attempt)

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=EmailLog.TYPE_COURSE_COMPLETED,
                quiz_attempt=self.attempt,
                status=EmailLog.STATUS_PREVIEW,
            ).count(),
            1,
        )
