from datetime import date

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from courses.emails.builders import (
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
from courses.emails.transport import send_email
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
    EMAIL_FROM_ACTIVATION="aktivace@example.com",
    EMAIL_FROM_INVOICES="faktury@example.com",
    EMAIL_FROM_CERTIFICATES="osvedceni@example.com",
    EMAIL_REPLY_TO="info@example.com",
)
class EmailSenderAddressTests(TestCase):
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
            contact_email="objednavka@example.com",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
            registration_number="EA-04-202608-00001",
        )

    def test_activation_uses_activation_sender(self):
        email = build_participant_activation_email(
            self.participant
        )

        self.assertEqual(
            email.from_email,
            "aktivace@example.com",
        )
        self.assertEqual(
            email.reply_to,
            ("info@example.com",),
        )

    def test_payment_email_uses_invoice_sender(self):
        email = build_payment_completed_email(
            self.order,
            [self.participant],
        )

        self.assertEqual(
            email.from_email,
            "faktury@example.com",
        )

    def test_course_completed_uses_certificate_sender(self):
        user = User.objects.create_user(
            username="jan@example.com",
            email="jan@example.com",
            password="Testheslo1",
        )

        self.participant.user = user
        self.participant.save(
            update_fields=["user"],
        )

        course = Course.objects.create(
            title="§4 – osoba poučená",
            description="Testovací kurz",
            video_url="https://example.com/video",
        )

        attempt = QuizAttempt.objects.create(
            user=user,
            course=course,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=20,
            correct_answers=18,
            score_percent=90,
            passed=True,
        )

        certificate = Certificate.objects.create(
            participant=self.participant,
            quiz_attempt=attempt,
            certificate_number="EA-04-202608-00001",
            valid_until=date(2029, 8, 9),
        )

        email = build_course_completed_email(
            attempt,
            certificate=certificate,
            certificate_pdf=b"%PDF certificate",
            quiz_result_pdf=b"%PDF result",
        )

        self.assertEqual(
            email.from_email,
            "osvedceni@example.com",
        )


@override_settings(
    EMAIL_TRANSPORT="smtp",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="smtp.example.com",
    EMAIL_USE_TLS=False,
    EMAIL_USE_SSL=False,
    DEFAULT_FROM_EMAIL="default@example.com",
)
class EmailSenderTransportTests(TestCase):
    def test_transport_uses_rendered_email_sender(self):
        from courses.emails.types import RenderedEmail

        email = RenderedEmail(
            subject="Test",
            recipient="recipient@example.com",
            text_body="Text",
            html_body="<p>Text</p>",
            from_email="aktivace@example.com",
            reply_to=("info@example.com",),
        )

        send_email(email)

        message = mail.outbox[0]

        self.assertEqual(
            message.from_email,
            "aktivace@example.com",
        )
        self.assertEqual(
            message.reply_to,
            ["info@example.com"],
        )

    def test_transport_falls_back_to_default_sender(self):
        from courses.emails.types import RenderedEmail

        email = RenderedEmail(
            subject="Test",
            recipient="recipient@example.com",
            text_body="Text",
            html_body="<p>Text</p>",
        )

        send_email(email)

        self.assertEqual(
            mail.outbox[0].from_email,
            "default@example.com",
        )
