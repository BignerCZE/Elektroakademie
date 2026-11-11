"""Contract tests: step checks and final writes use exactly the same forms."""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from courses.forms import BillingForm, ParticipantForm
from courses.models import Order, OrderParticipant
from courses.tests import test_registration


@override_settings(EMAIL_TRANSPORT="preview")
class CheckoutValidationTests(TestCase):
    def data(self, **changes):
        return {**test_registration.RegistrationTests().get_registration_data(), **changes}

    def validate(self, step="all", **changes):
        response = self.client.post(reverse("register"), self.data(_validate_step=step, **changes))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        return response.json()

    def test_valid_step_checks_do_not_create_records(self):
        for step in ("3", "4", "all"):
            self.assertTrue(self.validate(step)["valid"])
        self.assertFalse(OrderParticipant.objects.exists())

    def test_each_required_field_rejects_empty_and_spaces(self):
        names = [f"participants-0-{name}" for name in ParticipantForm.base_fields]
        names += [name for name, field in BillingForm.base_fields.items() if field.required]
        for name in names:
            for value in ("", "   "):
                with self.subTest(name=name, value=value):
                    result = self.validate(**{name: value})
                    self.assertIn(name, result["fields"])
                    self.assertFalse(result["valid"])

    def test_email_syntax_uses_django_not_only_html(self):
        for name in ("participants-0-email", "contact_email"):
            for value in ("random", "a@", "@example.cz", "a@firma", "a b@example.cz", "a@example..cz"):
                with self.subTest(name=name, value=value):
                    self.assertIn(name, self.validate(**{name: value})["fields"])
            self.assertTrue(self.validate(**{name: "  jan+kurz@example.cz  "})["valid"])

    def test_every_declared_length_limit_is_enforced(self):
        for form_class, prefix in ((ParticipantForm, "participants-0-"), (BillingForm, "")):
            for name, field in form_class.base_fields.items():
                if getattr(field, "max_length", None):
                    with self.subTest(field=prefix + name):
                        result = self.validate(**{prefix + name: "a" * (field.max_length + 1)})
                        self.assertIn(prefix + name, result["fields"])

    def test_phone_prefix_and_ico_rules(self):
        for name, invalids in {
            "contact_phone": ("abc", "12345", "777a123456"),
            "contact_phone_prefix": ("abc", "+", "++420", "12345678"),
            "ico": ("abc", "1234567", "12ab3456", "１２３４５６７８"),
        }.items():
            for value in invalids:
                with self.subTest(name=name, value=value):
                    self.assertIn(name, self.validate(**{name: value})["fields"])
        self.assertTrue(self.validate(ico="", contact_phone_prefix=" 421 ", contact_phone="777-123/456")["valid"])

    def test_no_invented_name_address_dic_or_postcode_restrictions(self):
        for country in ("CZ", "SK"):
            self.assertTrue(self.validate(country=country, company_name="Čížek & syn – servis, s.r.o.",
                street="Nábřeží 12/3", city="Frýdek-Místek", zip_code="700 30", dic="SK1234567890",
                **{"participants-0-first_name": "Anna-Marie", "participants-0-last_name": "D’Ángelo"})["valid"])
        self.assertIn("country", self.validate(country="XX")["fields"])

    def test_duplicate_and_existing_accounts_case_insensitive(self):
        data = self.data()
        data.update({"participants-TOTAL_FORMS": "2", "participants-1-first_name": "Petr",
            "participants-1-last_name": "Test", "participants-1-email": data["participants-0-email"].upper(),
            "_validate_step": "3"})
        result = self.client.post(reverse("register"), data).json()
        self.assertIn("participants-1-email", result["fields"])
        get_user_model().objects.create_user(username="JAN.NOVAK@EXAMPLE.COM", email="other@example.cz")
        self.assertIn("participants-0-email", self.validate()["fields"])

    def test_empty_added_participant_cannot_silently_disappear(self):
        result = self.validate(**{"participants-TOTAL_FORMS": "2", "participants-1-first_name": "",
            "participants-1-last_name": "", "participants-1-email": ""})
        self.assertIn("participants-1-first_name", result["fields"])

    def test_formset_management_errors_and_zero_people_are_visible(self):
        for value in ("bad", "0", "2001"):
            result = self.validate(**{"participants-TOTAL_FORMS": value})
            self.assertFalse(result["valid"])
            self.assertTrue(result["global"] or result["fields"])
        data = self.data(_validate_step="all")
        del data["participants-TOTAL_FORMS"]
        result = self.client.post(reverse("register"), data).json()
        self.assertTrue(result["global"])
        self.assertEqual(result["global"][0]["step"], 3)

    def test_current_step_ignores_unvisited_fields(self):
        self.assertTrue(self.validate("3", company_name="", terms_agreement="")["valid"])
        self.assertTrue(self.validate("4", **{"participants-0-email": "invalid", "terms_agreement": ""})["valid"])
        self.assertFalse(self.validate("all", **{"participants-0-email": "invalid"})["valid"])

    def test_final_post_preserves_values_and_opens_first_error_step(self):
        for name, step in (("participants-0-email", 3), ("contact_phone", 4), ("terms_agreement", 5)):
            data = self.data(**{name: "" if step == 5 else "invalid"})
            response = self.client.post(reverse("register"), data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["initial_step"], step)
            self.assertEqual(response.context["selected_course"], "4")
            self.assertTrue(response.context["registration_bound"])
            self.assertContains(response, 'value="Testovací firma s.r.o."')
            self.assertIn(name, response.context["validation_errors"]["fields"])
            self.assertFalse(Order.objects.exists())

    def test_missing_agreement_is_rejected_without_javascript_then_corrected(self):
        data = self.data()
        del data["terms_agreement"]
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.context["initial_step"], 5)
        self.assertFalse(Order.objects.exists())
        data["terms_agreement"] = "on"
        self.assertEqual(self.client.post(reverse("register"), data).status_code, 302)
        self.assertEqual(Order.objects.get().total_price, 990)

    def test_normalization_and_actual_group_write(self):
        data = self.data(contact_phone_prefix=" 420 ", contact_phone="777-123/456",
            company_name="  Čížek & syn  ", **{"participants-TOTAL_FORMS": "2",
            "participants-0-first_name": "  Anna-Marie  ", "participants-0-email": "  JAN@example.cz ",
            "participants-1-first_name": "Petr", "participants-1-last_name": "Čížek",
            "participants-1-email": "petr@example.cz"})
        self.assertEqual(self.client.post(reverse("register"), data).status_code, 302)
        order = Order.objects.get()
        self.assertEqual((order.total_price, order.participants.count()), (1980, 2))
        self.assertEqual(order.contact_phone, "777123456")
        self.assertEqual(order.contact_phone_prefix, "+420")
        self.assertEqual(order.participants.first().first_name, "Anna-Marie")
        self.assertEqual(order.participants.first().email, "jan@example.cz")

    def test_invalid_course_is_actionable(self):
        result = self.validate(selected_course="999")
        self.assertEqual(result["global"][0]["step"], 1)

    def test_validation_requests_still_require_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse("register"), self.data(_validate_step="all"))
        self.assertEqual(response.status_code, 403)
