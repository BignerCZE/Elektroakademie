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
            "employer_ico": "00123456",
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

        self.assertEqual(profile.employer_ico, "00123456")

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

        self.assertRedirects(response, reverse("index"))

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

    def test_optional_certificate_fields_support_legacy_activation(self):
        data = self.valid_data.copy()
        for field in ("employer_ico", "activity_scope", "workplace_specification"):
            data.pop(field, None)
        response = self.client.post(self.activation_url, data)
        self.assertEqual(response.status_code, 302)
        profile = ParticipantProfile.objects.get(participant=self.participant)
        self.assertEqual(profile.employer_ico, "")
        self.assertEqual(profile.activity_scope, "")
        self.assertEqual(profile.workplace_specification, "")

    def test_invalid_employer_ico_prevents_activation(self):
        data = {**self.valid_data, "employer_ico": "12ab3456"}
        response = self.client.post(self.activation_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IČO musí obsahovat přesně 8 číslic.")
        self.assertFalse(ParticipantProfile.objects.exists())

    def test_manual_certificate_fields_are_not_requested_at_activation(self):
        response = self.client.get(self.activation_url)
        self.assertNotContains(response, 'name="activity_scope"')
        self.assertNotContains(response, 'name="workplace_specification"')

    def test_restored_activation_revalidates_and_other_sessions_cannot_reuse_token(self):
        response = self.client.get(self.activation_url)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, "activation-history.js")
        self.client.post(self.activation_url, self.valid_data)
        self.assertRedirects(self.client.get(self.activation_url), reverse("index"))
        self.assertRedirects(self.client.post(self.activation_url, self.valid_data), reverse("index"))
        self.client.logout()
        response = self.client.get(self.activation_url)
        self.assertTemplateUsed(response, "registration/participant_activation_used.html")
        self.assertEqual(User.objects.count(), 1)


class OrderActivationJourneyTests(TestCase):
    def test_checkout_payment_activation_dashboard_and_return(self):
        from unittest.mock import patch
        from courses.models import Course, Invoice
        from courses.tests.test_registration import RegistrationTests
        Course.objects.create(title='Elektroakademie', description='Test', video_url='https://example.test/video')
        response = self.client.post(reverse('register'), RegistrationTests().get_registration_data())
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        simulation = self.client.get(reverse('order_payment_simulation', args=[order.pk]))
        self.assertContains(simulation, 'payment-countdown')
        with patch('courses.workflows.invoice_pdf', return_value=b'%PDF-test-only'):
            self.assertEqual(self.client.get(reverse('order_payment_success', args=[order.pk])).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(Invoice.objects.count(), 1)
        participant = OrderParticipant.objects.get(order=order)
        activation = reverse('participant_activation', args=[participant.activation_token])
        self.assertEqual(self.client.get(activation).status_code, 200)
        values = dict(password1='Testheslo1', password2='Testheslo1',
                      birth_day='15', birth_month='5', birth_year='1990',
                      birth_place='Praha', permanent_address='Testovací 1, Praha',
                      employer_name='Testovací firma', employer_ico='00123456',
                      employer_address='Testovací 1, Praha')
        self.assertRedirects(self.client.post(activation, values), reverse('dashboard'))
        participant.refresh_from_db()
        dashboard = self.client.get(reverse('dashboard'))
        self.assertTrue(dashboard.wsgi_request.user.is_authenticated)
        self.assertTrue(participant.user.is_paid)
        self.assertContains(dashboard, 'Přehrát výukové video')
        self.assertRedirects(self.client.get(activation), reverse('index'))
        self.assertEqual(User.objects.count(), 1)
