import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Order, OrderParticipant


User = get_user_model()


class RegistrationTests(TestCase):

    def test_existing_user_email_cannot_be_registered_as_participant(
        self,
    ):
        User.objects.create_user(
            username="jan.novak@example.com",
            email="jan.novak@example.com",
            password="PuvodniHeslo1",
        )

        response = self.client.post(
            reverse("register"),
            self.get_registration_data(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.assertEqual(
            OrderParticipant.objects.count(),
            0,
        )   
        
    def get_registration_data(
        self,
        participants=None,
        selected_course="4",
    ):
        if participants is None:
            participants = [
                {
                    "first_name": "Jan",
                    "last_name": "Novák",
                    "email": "jan.novak@example.com",
                }
            ]

        data = {
            "selected_course": selected_course,
            "participants-TOTAL_FORMS": str(len(participants)),
            "participants-INITIAL_FORMS": "0",
            "participants-MIN_NUM_FORMS": "1",
            "participants-MAX_NUM_FORMS": "1000",
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

        for index, participant in enumerate(participants):
            data[
                f"participants-{index}-first_name"
            ] = participant["first_name"]

            data[
                f"participants-{index}-last_name"
            ] = participant["last_name"]

            data[
                f"participants-{index}-email"
            ] = participant["email"]

        return data

    def test_registration_page_is_available(self):
        response = self.client.get(
            reverse("register")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "registration/register.html",
        )

    def test_valid_registration_creates_order(self):
        response = self.client.post(
            reverse("register"),
            self.get_registration_data(),
        )

        self.assertEqual(
            Order.objects.count(),
            1,
        )

        order = Order.objects.get()

        self.assertEqual(
            order.course_type,
            "4",
        )
        self.assertEqual(
            order.status,
            "pending_payment",
        )
        self.assertEqual(
            order.total_price,
            990,
        )

        self.assertEqual(
            order.company_name,
            "Testovací firma s.r.o.",
        )

        self.assertEqual(
            order.contact_first_name,
            "Petr",
        )
        self.assertEqual(
            order.contact_last_name,
            "Svoboda",
        )

        self.assertEqual(
            order.contact_phone_prefix,
            "+420",
        )

        self.assertEqual(
            order.contact_phone,
            "777123456",
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "order_payment_simulation",
                kwargs={
                    "order_id": order.id,
                },
            ),
        )

    def test_valid_registration_creates_participant(self):
        self.client.post(
            reverse("register"),
            self.get_registration_data(),
        )

        self.assertEqual(
            OrderParticipant.objects.count(),
            1,
        )

        participant = OrderParticipant.objects.get()

        self.assertEqual(
            participant.first_name,
            "Jan",
        )
        self.assertEqual(
            participant.last_name,
            "Novák",
        )
        self.assertEqual(
            participant.email,
            "jan.novak@example.com",
        )

    def test_participant_email_is_normalized(self):
        data = self.get_registration_data(
            participants=[
                {
                    "first_name": "Jan",
                    "last_name": "Novák",
                    "email": "JAN.NOVAK@EXAMPLE.COM",
                }
            ]
        )

        self.client.post(
            reverse("register"),
            data,
        )

        participant = OrderParticipant.objects.get()

        self.assertEqual(
            participant.email,
            "jan.novak@example.com",
        )

    def test_multiple_participants_set_correct_total_price(self):
        data = self.get_registration_data(
            participants=[
                {
                    "first_name": "Jan",
                    "last_name": "Novák",
                    "email": "jan@example.com",
                },
                {
                    "first_name": "Petr",
                    "last_name": "Svoboda",
                    "email": "petr@example.com",
                },
            ]
        )

        self.client.post(
            reverse("register"),
            data,
        )

        order = Order.objects.get()

        self.assertEqual(
            order.total_price,
            1980,
        )

        self.assertEqual(
            order.participants.count(),
            2,
        )

    def test_duplicate_email_in_same_order_is_rejected(self):
        data = self.get_registration_data(
            participants=[
                {
                    "first_name": "Jan",
                    "last_name": "Novák",
                    "email": "jan@example.com",
                },
                {
                    "first_name": "Petr",
                    "last_name": "Svoboda",
                    "email": "JAN@example.com",
                },
            ]
        )

        response = self.client.post(
            reverse("register"),
            data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.assertEqual(
            OrderParticipant.objects.count(),
            0,
        )

        self.assertContains(
            response,
            (
                "Tato e-mailová adresa je v objednávce "
                "uvedena vícekrát."
            ),
        )

    def test_invalid_course_does_not_create_order(self):
        response = self.client.post(
            reverse("register"),
            self.get_registration_data(
                selected_course="999"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.assertEqual(
            OrderParticipant.objects.count(),
            0,
        )

    def test_missing_required_billing_data_does_not_create_order(
        self,
    ):
        data = self.get_registration_data()
        data["company_name"] = ""

        response = self.client.post(
            reverse("register"),
            data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.assertEqual(
            OrderParticipant.objects.count(),
            0,
        )

    def test_existing_user_email_is_reported_as_occupied(self):
        User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="Testheslo1",
        )

        response = self.client.post(
            reverse("check_participant_emails"),
            data=json.dumps(
                {
                    "emails": [
                        "existing@example.com",
                        "free@example.com",
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["success"]
        )

        self.assertEqual(
            payload["occupied_emails"],
            ["existing@example.com"],
        )

        self.assertEqual(
            payload["duplicate_emails"],
            [],
        )

    def test_duplicate_submitted_emails_are_reported(self):
        response = self.client.post(
            reverse("check_participant_emails"),
            data=json.dumps(
                {
                    "emails": [
                        "jan@example.com",
                        "JAN@example.com",
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertEqual(
            payload["duplicate_emails"],
            ["jan@example.com"],
        )

    def test_invalid_email_check_json_returns_400(self):
        response = self.client.post(
            reverse("check_participant_emails"),
            data="{invalid-json",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            response.json()["success"]
        )

    def test_email_check_requires_list(self):
        response = self.client.post(
            reverse("check_participant_emails"),
            data=json.dumps(
                {
                    "emails": "jan@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            response.json()["success"]
        )

    def test_email_check_requires_post(self):
        response = self.client.get(
            reverse("check_participant_emails")
        )

        self.assertEqual(
            response.status_code,
            405,
        )



