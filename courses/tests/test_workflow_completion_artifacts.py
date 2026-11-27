from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from courses.emails.transport import send_email
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

    @override_settings(
        EMAIL_TRANSPORT="smtp_test", COMGATE_TEST=True, COMGATE_LIVE=False,
        EMAIL_TEST_RECIPIENTS=("artifact@example.com",),
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_FROM_CERTIFICATES="osvedceni@elektroakademie.cz",
        SITE_URL="https://elektroakademie.cz",
    )
    @patch("courses.workflows.generate_quiz_result_pdf", return_value=b"%PDF quiz")
    @patch("courses.workflows.generate_certificate_pdf", return_value=b"%PDF certificate")
    def test_allowlisted_quiz_completion_delivers_certificate_and_result(self, _certificate, _quiz):
        for _ in range(2):
            self.assertEqual(process_quiz_completion(self.attempt).errors, ())
        message, = mail.outbox
        self.assertEqual(message.from_email, "osvedceni@elektroakademie.cz")
        self.assertEqual(message.to, [self.user.email])
        self.assertCountEqual(
            [(attachment.content, attachment.mimetype) for attachment in message.attachments],
            [(b"%PDF certificate", "application/pdf"), (b"%PDF quiz", "application/pdf")],
        )
        logs = EmailLog.objects.filter(quiz_attempt=self.attempt)
        self.assertEqual(logs.get(email_type=EmailLog.TYPE_COURSE_COMPLETED).status, EmailLog.STATUS_SENT)
        self.assertEqual(
            logs.get(email_type=EmailLog.TYPE_ORDER_CONTACT_COURSE_COMPLETED).status,
            EmailLog.STATUS_PREVIEW,
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
        self.assertTrue(EmailLog.objects.filter(
            quiz_attempt=self.attempt,
            order=self.order,
            email_type=EmailLog.TYPE_ORDER_CONTACT_COURSE_COMPLETED,
            status=EmailLog.STATUS_PREVIEW,
        ).exists())

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


    @override_settings(
        EMAIL_TRANSPORT="smtp_test", COMGATE_TEST=True, COMGATE_LIVE=False,
        EMAIL_TEST_RECIPIENTS=("artifact@example.com", "kontakt@example.com"),
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
    )
    @patch("courses.workflows.generate_quiz_result_pdf", return_value=b"%PDF quiz")
    @patch("courses.workflows.generate_certificate_pdf", return_value=b"%PDF certificate")
    def test_contact_retry_sends_only_certificate_without_resending_participant(self, _certificate, quiz):
        def reject_contact(email):
            if email.recipient == self.order.contact_email:
                raise ConnectionError("SMTP nedostupné")
            return send_email(email)

        with patch("courses.emails.delivery.send_email", side_effect=reject_contact):
            self.assertTrue(process_quiz_completion(self.attempt).errors)
        participant_message, = mail.outbox
        self.assertEqual(participant_message.to, [self.user.email])

        for _ in range(2):
            self.assertEqual(process_quiz_completion(self.attempt).errors, ())

        self.assertEqual(len(mail.outbox), 2)
        contact_message = mail.outbox[1]
        self.assertEqual(contact_message.to, [self.order.contact_email])
        attachment, = contact_message.attachments
        self.assertEqual(attachment.content, b"%PDF certificate")
        parts = contact_message.message().get_payload()
        pdf_parts = [part for part in parts if part.get_content_type() == "application/pdf"]
        pdf_part, = pdf_parts
        self.assertEqual(pdf_part.get_content_disposition(), "attachment")
        self.assertTrue(pdf_part.get_filename().endswith(".pdf"))
        self.assertEqual(pdf_part.get_payload(decode=True), b"%PDF certificate")
        self.assertIn(f"objednávky č. {self.order.pk}", contact_message.body)
        self.assertIn("Jan Novák", contact_message.body)
        quiz.assert_called_once()

    @patch("courses.workflows.generate_quiz_result_pdf", return_value=b"%PDF quiz")
    @patch("courses.workflows.generate_certificate_pdf", return_value=b"%PDF certificate")
    def test_shared_contact_address_receives_only_participant_email(self, _certificate, _quiz):
        self.order.contact_email = self.user.email.upper()
        self.order.save(update_fields=["contact_email"])
        self.assertEqual(process_quiz_completion(self.attempt).errors, ())
        log = EmailLog.objects.get(quiz_attempt=self.attempt)
        self.assertEqual(log.email_type, EmailLog.TYPE_COURSE_COMPLETED)

    @patch("courses.workflows.generate_quiz_result_pdf", return_value=b"%PDF quiz")
    @patch("courses.workflows.generate_certificate_pdf", return_value=b"%PDF certificate")
    def test_contact_email_admin_preview_and_download(self, _certificate, _quiz):
        self.assertEqual(process_quiz_completion(self.attempt).errors, ())
        log = EmailLog.objects.get(email_type=EmailLog.TYPE_ORDER_CONTACT_COURSE_COMPLETED)
        url = reverse("order_contact_course_completed_email_preview", args=[log.pk])
        self.assertEqual(self.client.get(url + "?format=pdf").status_code, 302)
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url + "?format=pdf").status_code, 403)
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        for admin_url in (
            reverse("admin:courses_emaillog_changelist"),
            reverse("admin:courses_emaillog_change", args=[log.pk]),
        ):
            self.assertContains(self.client.get(admin_url), url)
        self.assertContains(self.client.get(url), log.recipient)
        self.assertContains(self.client.get(url), "?format=pdf")
        with patch("courses.views.generate_certificate_pdf", return_value=b"%PDF certificate"):
            response = self.client.get(url + "?format=pdf")
        self.assertEqual(response.content, b"%PDF certificate")
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
