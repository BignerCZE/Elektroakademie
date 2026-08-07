import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from django.urls import reverse
from datetime import date

from unittest.mock import patch

from courses.emails.transport import (
    EmailDeliveryResult,
    PreviewEmailTransport,
    get_email_transport,
    send_email,
)

from courses.emails.builders import (
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)

from courses.emails.types import RenderedEmail
from courses.models import Order, OrderParticipant

from unittest.mock import patch

from courses.models import (
    Certificate,
    Course,
    Order,
    OrderParticipant,
    QuizAttempt,
)

User = get_user_model()




@override_settings(
    SITE_URL="https://elektroakademie.test",
)
class ParticipantActivationEmailBuilderTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan.novak@example.com",
            registration_number="EA-04-202608-00001",
        )

    def test_builder_returns_rendered_email(self):
        email = build_participant_activation_email(
            self.participant
        )

        self.assertIsInstance(
            email,
            RenderedEmail,
        )

    def test_builder_sets_recipient_and_subject(self):
        email = build_participant_activation_email(
            self.participant
        )

        self.assertEqual(
            email.recipient,
            "jan.novak@example.com",
        )

        self.assertEqual(
            email.subject,
            "Aktivace přístupu do Elektroakademie",
        )

    def test_html_body_contains_participant_data(self):
        email = build_participant_activation_email(
            self.participant
        )

        self.assertIn(
            "Jan",
            email.html_body,
        )
        self.assertIn(
            "Novák",
            email.html_body,
        )
        self.assertIn(
            "EA-04-202608-00001",
            email.html_body,
        )
        self.assertIn(
            "§4 – osoba poučená",
            email.html_body,
        )

    def test_text_body_contains_participant_data(self):
        email = build_participant_activation_email(
            self.participant
        )

        self.assertIn(
            "Jan",
            email.text_body,
        )
        self.assertIn(
            "Novák",
            email.text_body,
        )
        self.assertIn(
            "EA-04-202608-00001",
            email.text_body,
        )
        self.assertIn(
            "§4 – osoba poučená",
            email.text_body,
        )

    def test_bodies_contain_absolute_activation_url(self):
        email = build_participant_activation_email(
            self.participant
        )

        activation_path = reverse(
            "participant_activation",
            kwargs={
                "token": self.participant.activation_token,
            },
        )

        expected_url = (
            f"https://elektroakademie.test"
            f"{activation_path}"
        )

        self.assertIn(
            expected_url,
            email.html_body,
        )
        self.assertIn(
            expected_url,
            email.text_body,
        )

    def test_builder_does_not_change_participant(self):
        original_token = self.participant.activation_token

        build_participant_activation_email(
            self.participant
        )

        self.participant.refresh_from_db()

        self.assertEqual(
            self.participant.activation_token,
            original_token,
        )
        self.assertIsNone(
            self.participant.activation_sent_at,
        )
        self.assertIsNone(
            self.participant.activation_completed_at,
        )
        self.assertIsNone(
            self.participant.user,
        )


@override_settings(
    SITE_URL="https://elektroakademie.test",
)
class ParticipantActivationEmailPreviewTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan.novak@example.com",
            registration_number="EA-04-202608-00001",
        )

        self.preview_url = reverse(
            "participant_activation_email_preview",
            kwargs={
                "token": self.participant.activation_token,
            },
        )

        self.staff_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Testheslo1",
            is_staff=True,
        )

    def test_staff_user_can_view_html_preview(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response["Content-Type"],
            "text/html; charset=utf-8",
        )

        self.assertContains(
            response,
            "Dokončete aktivaci svého účtu",
        )
        self.assertContains(
            response,
            "Jan",
        )
        self.assertContains(
            response,
            "EA-04-202608-00001",
        )

    def test_staff_user_can_view_text_preview(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            f"{self.preview_url}?format=text"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response["Content-Type"],
            "text/plain; charset=utf-8",
        )

        content = response.content.decode("utf-8")

        self.assertIn(
            "ELEKTROAKADEMIE",
            content,
        )
        self.assertIn(
            "Jan",
            content,
        )
        self.assertIn(
            "EA-04-202608-00001",
            content,
        )

    def test_anonymous_user_cannot_view_preview(self):
        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_non_staff_user_cannot_view_preview(self):
        user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="Testheslo1",
        )

        self.client.force_login(user)

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_invalid_preview_format_returns_400(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            f"{self.preview_url}?format=invalid"
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.content.decode("utf-8"),
            "Neplatný formát náhledu.",
        )

    def test_unknown_participant_returns_404(self):
        self.client.force_login(self.staff_user)

        url = reverse(
            "participant_activation_email_preview",
            kwargs={
                "token": uuid.uuid4(),
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_preview_does_not_mark_email_as_sent(self):
        self.client.force_login(self.staff_user)

        self.client.get(
            self.preview_url
        )

        self.participant.refresh_from_db()

        self.assertIsNone(
            self.participant.activation_sent_at,
        )



@patch(
    "courses.emails.builders.generate_quiz_result_pdf",
    return_value=b"%PDF quiz",
)
@patch(
    "courses.emails.builders.generate_certificate_pdf",
    return_value=b"%PDF certificate",
)
def test_course_completed_email_has_two_pdf_attachments(
    self,
    mock_certificate_pdf,
    mock_quiz_pdf,
):
    email = build_course_completed_email(
        self.attempt
    )

    self.assertEqual(
        len(email.attachments),
        2,
    )

    certificate_attachment = email.attachments[0]
    quiz_attachment = email.attachments[1]

    self.assertEqual(
        certificate_attachment.mimetype,
        "application/pdf",
    )

    self.assertEqual(
        quiz_attachment.mimetype,
        "application/pdf",
    )

    self.assertEqual(
        certificate_attachment.content,
        b"%PDF certificate",
    )

    self.assertEqual(
        quiz_attachment.content,
        b"%PDF quiz",
    )

class CourseCompletedEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jan@example.com",
            email="jan@example.com",
            password="Testheslo1",
            first_name="Jan",
            last_name="Novák",
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
            country="CZ",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
            registration_number="EA-04-202608-00001",
        )

        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=20,
            correct_answers=18,
            score_percent=90,
            passed=True,
        )

        self.certificate = Certificate.objects.create(
            participant=self.participant,
            quiz_attempt=self.attempt,
            certificate_number="EA-04-202608-00001",
            valid_until=date(
                2029,
                8,
                6,
            ),
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_builder_creates_course_completed_email(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        email = build_course_completed_email(
            self.attempt
        )

        self.assertIsInstance(
            email,
            RenderedEmail,
        )

        self.assertEqual(
            email.recipient,
            "jan@example.com",
        )

        self.assertEqual(
            email.subject,
            (
                "Úspěšné dokončení kurzu – "
                "certifikát a výsledek testu"
            ),
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_email_contains_two_pdf_attachments(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        email = build_course_completed_email(
            self.attempt
        )

        self.assertEqual(
            len(email.attachments),
            2,
        )

        certificate_attachment = (
            email.attachments[0]
        )

        quiz_attachment = (
            email.attachments[1]
        )

        self.assertEqual(
            certificate_attachment.mimetype,
            "application/pdf",
        )

        self.assertEqual(
            quiz_attachment.mimetype,
            "application/pdf",
        )

        self.assertEqual(
            certificate_attachment.content,
            b"%PDF certificate",
        )

        self.assertEqual(
            quiz_attachment.content,
            b"%PDF quiz result",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_attachment_filenames_are_correct(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        email = build_course_completed_email(
            self.attempt
        )

        self.assertEqual(
            email.attachments[0].filename,
            "certifikat-EA-04-202608-00001.pdf",
        )

        self.assertEqual(
            email.attachments[1].filename,
            f"vysledek-testu-{self.attempt.id}.pdf",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_email_contains_course_result_data(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        email = build_course_completed_email(
            self.attempt
        )

        self.assertIn(
            "§4 – osoba poučená",
            email.html_body,
        )

        self.assertIn(
            "90",
            email.html_body,
        )

        self.assertIn(
            "EA-04-202608-00001",
            email.html_body,
        )

        self.assertIn(
            "SPLNĚNO",
            email.text_body,
        )

    def test_failed_attempt_cannot_build_email(self):
        self.attempt.passed = False
        self.attempt.save(
            update_fields=["passed"]
        )

        with self.assertRaises(ValueError):
            build_course_completed_email(
                self.attempt
            )

    def test_in_progress_attempt_cannot_build_email(self):
        self.attempt.status = (
            QuizAttempt.STATUS_IN_PROGRESS
        )

        self.attempt.save(
            update_fields=["status"]
        )

        with self.assertRaises(ValueError):
            build_course_completed_email(
                self.attempt
            )

    def test_missing_certificate_cannot_build_email(self):
        self.certificate.delete()

        with self.assertRaises(ValueError):
            build_course_completed_email(
                self.attempt
            )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_builder_generates_both_pdf_documents(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        build_course_completed_email(
            self.attempt
        )

        mock_certificate_pdf.assert_called_once_with(
            self.certificate
        )

        mock_quiz_result_pdf.assert_called_once_with(
            self.attempt
        )

class CourseCompletedEmailPreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jan@example.com",
            email="jan@example.com",
            password="Testheslo1",
            first_name="Jan",
            last_name="Novák",
        )

        self.staff_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Testheslo1",
            is_staff=True,
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
            country="CZ",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
            registration_number="EA-04-202608-00001",
        )

        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=20,
            correct_answers=18,
            score_percent=90,
            passed=True,
        )

        self.certificate = Certificate.objects.create(
            participant=self.participant,
            quiz_attempt=self.attempt,
            certificate_number="EA-04-202608-00001",
            valid_until=date(
                2029,
                8,
                6,
            ),
        )

        self.preview_url = reverse(
            "course_completed_email_preview",
            kwargs={
                "attempt_id": self.attempt.id,
            },
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_staff_can_view_preview(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "jan@example.com",
        )

        self.assertContains(
            response,
            "certifikat-EA-04-202608-00001.pdf",
        )

        self.assertContains(
            response,
            f"vysledek-testu-{self.attempt.id}.pdf",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_staff_can_view_html_version(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            f"{self.preview_url}?format=html"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "text/html; charset=utf-8",
        )

        self.assertContains(
            response,
            "Kurz jste úspěšně dokončili",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_staff_can_view_text_version(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            f"{self.preview_url}?format=text"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "text/plain; charset=utf-8",
        )

        content = response.content.decode(
            "utf-8"
        )

        self.assertIn(
            "SPLNĚNO",
            content,
        )

    def test_anonymous_user_cannot_view_preview(self):
        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_non_staff_user_cannot_view_preview(self):
        self.client.force_login(
            self.user
        )

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_invalid_format_returns_400(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            f"{self.preview_url}?format=invalid"
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_first_attachment_returns_certificate_pdf(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        url = reverse(
            "course_completed_email_attachment",
            kwargs={
                "attempt_id": self.attempt.id,
                "attachment_index": 0,
            },
        )

        response = self.client.get(url)

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
            b"%PDF certificate",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_second_attachment_returns_quiz_pdf(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        url = reverse(
            "course_completed_email_attachment",
            kwargs={
                "attempt_id": self.attempt.id,
                "attachment_index": 1,
            },
        )

        response = self.client.get(url)

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
            b"%PDF quiz result",
        )

    @patch(
        "courses.emails.builders.generate_quiz_result_pdf",
        return_value=b"%PDF quiz result",
    )
    @patch(
        "courses.emails.builders.generate_certificate_pdf",
        return_value=b"%PDF certificate",
    )
    def test_unknown_attachment_returns_404(
        self,
        mock_certificate_pdf,
        mock_quiz_result_pdf,
    ):
        self.client.force_login(
            self.staff_user
        )

        url = reverse(
            "course_completed_email_attachment",
            kwargs={
                "attempt_id": self.attempt.id,
                "attachment_index": 99,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

class EmailTransportTests(TestCase):
    def setUp(self):
        self.email = RenderedEmail(
            subject="Testovací e-mail",
            recipient="jan@example.com",
            text_body="Textová verze",
            html_body="<p>HTML verze</p>",
        )

    @override_settings(
        EMAIL_TRANSPORT="preview",
    )
    def test_preview_transport_is_selected(self):
        transport = get_email_transport()

        self.assertIsInstance(
            transport,
            PreviewEmailTransport,
        )

    @override_settings(
        EMAIL_TRANSPORT="preview",
    )
    def test_preview_transport_returns_preview_result(self):
        result = send_email(
            self.email
        )

        self.assertIsInstance(
            result,
            EmailDeliveryResult,
        )

        self.assertEqual(
            result.status,
            "preview",
        )

        self.assertEqual(
            result.recipient,
            "jan@example.com",
        )

    @override_settings(
        EMAIL_TRANSPORT="unknown",
    )
    def test_unknown_transport_raises_error(self):
        with self.assertRaises(ValueError):
            get_email_transport()

    @override_settings(
        EMAIL_TRANSPORT="preview",
    )
    def test_preview_transport_does_not_change_email(self):
        original_email = self.email

        send_email(
            self.email
        )

        self.assertEqual(
            self.email,
            original_email,
        )

class PaymentCompletedEmailPreviewTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Testheslo1",
            is_staff=True,
        )

        self.normal_user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="Testheslo1",
        )

        self.order = Order.objects.create(
            course_type="4",
            total_price=1980,
            status="paid",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
            contact_first_name="Petr",
            contact_last_name="Svoboda",
            contact_email="kontakt@example.com",
        )

        OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
        )

        OrderParticipant.objects.create(
            order=self.order,
            first_name="Eva",
            last_name="Nováková",
            email="eva@example.com",
        )

        self.preview_url = reverse(
            "payment_completed_email_preview",
            kwargs={
                "order_id": self.order.id,
            },
        )

    def test_staff_can_view_html_preview(self):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "text/html; charset=utf-8",
        )

        self.assertContains(
            response,
            "Platba byla úspěšně přijata",
        )

        self.assertContains(
            response,
            "Jan",
        )

        self.assertContains(
            response,
            "Eva",
        )

    def test_staff_can_view_text_preview(self):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            f"{self.preview_url}?format=text"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "text/plain; charset=utf-8",
        )

        content = response.content.decode(
            "utf-8"
        )

        self.assertIn(
            "Jan Novák",
            content,
        )

        self.assertIn(
            "Eva Nováková",
            content,
        )

    def test_invalid_format_returns_400(self):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            f"{self.preview_url}?format=invalid"
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_anonymous_user_cannot_view_preview(self):
        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_non_staff_user_cannot_view_preview(self):
        self.client.force_login(
            self.normal_user
        )

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_unpaid_order_returns_404(self):
        self.order.status = "pending_payment"
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.preview_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )