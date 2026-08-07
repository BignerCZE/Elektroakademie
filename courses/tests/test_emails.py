import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.emails.builders import (
    build_order_confirmation_email,
    build_participant_activation_email,
)

from courses.emails.types import RenderedEmail
from courses.models import Order, OrderParticipant


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

class OrderConfirmationEmailTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=1980,
            status="pending_payment",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="Česká republika",
            contact_first_name="Petr",
            contact_last_name="Svoboda",
            contact_email="petr@example.com",
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

    def test_builder_returns_order_confirmation_email(self):
        email = build_order_confirmation_email(
            self.order
        )

        self.assertIsInstance(
            email,
            RenderedEmail,
        )

        self.assertEqual(
            email.recipient,
            "petr@example.com",
        )

        self.assertEqual(
            email.subject,
            f"Potvrzení objednávky č. {self.order.id} – Elektroakademie",
        )

    def test_email_contains_order_data(self):
        email = build_order_confirmation_email(
            self.order
        )

        self.assertIn(
            "§4 – osoba poučená",
            email.html_body,
        )
        self.assertIn(
            "1980",
            email.html_body,
        )
        self.assertIn(
            "Jan",
            email.html_body,
        )
        self.assertIn(
            "Eva",
            email.html_body,
        )

        self.assertIn(
            "1980",
            email.text_body,
        )
        self.assertIn(
            "jan@example.com",
            email.text_body,
        )

    def test_builder_does_not_change_order(self):
        original_status = self.order.status

        build_order_confirmation_email(
            self.order
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            original_status,
        )