from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import (
    Order,
    OrderParticipant,
    ParticipantProfile,
)


User = get_user_model()


class ParticipantActivationTests(TestCase):

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

        self.activation_url = reverse(
            "participant_activation",
            kwargs={
                "token": self.participant.activation_token,
            },
        )

        self.valid_data = {
            "password1": "Testheslo1",
            "password2": "Testheslo1",
            "birth_day": "15",
            "birth_month": "5",
            "birth_year": "1990",
            "birth_place": "Praha",
            "permanent_address": "Dlouhá 10, Praha",
            "employer_name": "Testovací firma s.r.o.",
            "employer_address": (
                "Testovací 1, 11000 Praha, Česká republika"
            ),
        }

    def test_unpaid_order_cannot_be_activated(self):
        self.order.status = "pending_payment"
        self.order.save(update_fields=["status"])

        response = self.client.get(self.activation_url)

        self.assertEqual(response.status_code, 403)

        self.assertTemplateUsed(
            response,
            "registration/participant_activation_unavailable.html",
        )

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(ParticipantProfile.objects.count(), 0)

    def test_activation_page_is_available_for_paid_order(self):
        response = self.client.get(self.activation_url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "registration/participant_activation.html",
        )

        self.assertContains(
            response,
            "Testovací firma s.r.o.",
        )

        self.assertContains(response, 'name="birth_day"')
        self.assertContains(response, 'name="birth_month"')
        self.assertContains(response, 'name="birth_year"')
        self.assertNotContains(response, 'name="birth_date"')

    def test_leap_day_is_accepted(self):
        data = {
            **self.valid_data,
            "birth_day": "29",
            "birth_month": "2",
            "birth_year": "2000",
        }

        response = self.client.post(self.activation_url, data)

        self.assertRedirects(response, reverse("dashboard"))
        profile = ParticipantProfile.objects.get(participant=self.participant)
        self.assertEqual(str(profile.birth_date), "2000-02-29")

    def test_invalid_calendar_date_is_rejected_and_preserved(self):
        data = {
            **self.valid_data,
            "birth_day": "29",
            "birth_month": "2",
            "birth_year": "2023",
        }

        response = self.client.post(self.activation_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zadané datum narození neexistuje.")
        self.assertContains(response, 'value="29"')
        self.assertContains(response, 'value="2023"')
        self.assertContains(response, "activation-date--error")
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(ParticipantProfile.objects.count(), 0)

    def test_missing_required_fields_are_highlighted(self):
        data = {
            **self.valid_data,
            "birth_day": "",
            "birth_place": "",
        }

        response = self.client.post(self.activation_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vyplňte den.")
        self.assertContains(response, "Toto pole je třeba vyplnit.")
        self.assertContains(response, "activation-date--error")
        self.assertContains(response, "activation-field--error")
        self.assertContains(response, 'value="Dlouhá 10, Praha"')
        self.assertEqual(User.objects.count(), 0)

    def test_successful_activation_creates_user(self):
        response = self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get()

        self.assertEqual(
            user.username,
            "jan.novak@example.com",
        )
        self.assertEqual(
            user.email,
            "jan.novak@example.com",
        )
        self.assertEqual(user.first_name, "Jan")
        self.assertEqual(user.last_name, "Novák")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_paid)

    def test_successful_activation_sets_password(self):
        self.client.post(
            self.activation_url,
            self.valid_data,
        )

        user = User.objects.get(
            username="jan.novak@example.com",
        )

        self.assertTrue(
            user.check_password("Testheslo1")
        )

        self.assertFalse(
            user.check_password("SpatneHeslo1")
        )

    def test_successful_activation_creates_profile(self):
        self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertEqual(
            ParticipantProfile.objects.count(),
            1,
        )

        profile = ParticipantProfile.objects.get(
            participant=self.participant,
        )

        self.assertEqual(
            str(profile.birth_date),
            "1990-05-15",
        )
        self.assertEqual(
            profile.birth_place,
            "Praha",
        )
        self.assertEqual(
            profile.permanent_address,
            "Dlouhá 10, Praha",
        )
        self.assertEqual(
            profile.employer_name,
            "Testovací firma s.r.o.",
        )
        self.assertEqual(
            profile.employer_address,
            (
                "Testovací 1, 11000 Praha, "
                "Česká republika"
            ),
        )

    def test_successful_activation_links_user_to_participant(self):
        self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.participant.refresh_from_db()

        self.assertIsNotNone(self.participant.user)
        self.assertIsNotNone(
            self.participant.activation_completed_at
        )

        self.assertEqual(
            self.participant.user.email,
            "jan.novak@example.com",
        )

    def test_user_is_logged_in_after_activation(self):
        self.client.post(
            self.activation_url,
            self.valid_data,
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            response.wsgi_request.user.is_authenticated
        )

        self.assertEqual(
            response.wsgi_request.user.email,
            "jan.novak@example.com",
        )

    def test_used_activation_link_does_not_create_second_user(self):
        self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertEqual(User.objects.count(), 1)

        response = self.client.get(
            self.activation_url
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "registration/participant_activation_used.html",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            ParticipantProfile.objects.count(),
            1,
        )

    def test_existing_user_blocks_activation(self):
        existing_user = User.objects.create_user(
            username="jan.novak@example.com",
            email="jan.novak@example.com",
            password="PuvodniHeslo1",
        )

        response = self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertEqual(response.status_code, 409)

        self.assertEqual(User.objects.count(), 1)

        self.participant.refresh_from_db()

        self.assertIsNone(self.participant.user)
        self.assertIsNone(
            self.participant.activation_completed_at
        )

        self.assertEqual(
            ParticipantProfile.objects.count(),
            0,
        )

        existing_user.refresh_from_db()

        self.assertTrue(
            existing_user.check_password(
                "PuvodniHeslo1"
            )
        )

        self.assertFalse(
            existing_user.check_password(
                "Testheslo1"
            )
        )

    def test_existing_username_also_blocks_activation(self):
        User.objects.create_user(
            username="jan.novak@example.com",
            email="jiny@example.com",
            password="PuvodniHeslo1",
        )

        response = self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.count(), 1)

        self.participant.refresh_from_db()

        self.assertIsNone(self.participant.user)
        self.assertIsNone(
            self.participant.activation_completed_at
        )

    def test_email_is_normalized_during_activation(self):
        self.participant.email = "  JAN.NOVAK@EXAMPLE.COM  "
        self.participant.save(update_fields=["email"])

        response = self.client.post(
            self.activation_url,
            self.valid_data,
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
        )

        user = User.objects.get()

        self.assertEqual(
            user.username,
            "jan.novak@example.com",
        )
        self.assertEqual(
            user.email,
            "jan.novak@example.com",
        )
