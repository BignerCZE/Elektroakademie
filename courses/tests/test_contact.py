from smtplib import SMTPException
from unittest.mock import patch

import requests
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from courses.contact import TURNSTILE_URL


@override_settings(
    EMAIL_TRANSPORT="smtp_test",
    EMAIL_TEST_RECIPIENTS=("formular@example.com",),
    COMGATE_TEST=True,
    COMGATE_LIVE=False,
    EMAIL_HOST="smtp.example.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_EMAIL_RECIPIENT="formular@example.com",
    CONTACT_FROM_EMAIL="odesilatel@example.com",
    SITE_URL="https://elektroakademie.cz",
    TURNSTILE_SITE_KEY="site-key",
    TURNSTILE_SECRET_KEY="secret-key",
)
class ContactSubmissionTests(TestCase):
    def setUp(self):
        self.url = reverse("index")
        self.data = {
            "name": "Jana Nováková", "email": "jana@example.com", "phone": "",
            "topic": "paragraf-6", "message": "Ráda bych se přihlásila na školení.",
            "cf-turnstile-response": "test-token",
        }
        self.verify = self.enterContext(patch("courses.contact.requests.post"))
        self.verify.return_value.status_code = 200
        self.verify.return_value.json.return_value = {
            "success": True, "hostname": "elektroakademie.cz", "action": "contact",
        }

    def test_csrf_and_confirmed_delivery_with_reply_to_and_one_time_feedback(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        self.verify.assert_not_called()
        page = client.get(self.url)
        self.assertContains(page, 'data-sitekey="site-key"')
        self.assertNotContains(page, "secret-key")
        token = client.cookies["csrftoken"].value
        response = client.post(self.url, self.data, headers={"X-CSRFToken": token})
        self.assertRedirects(response, self.url + "#contact", fetch_redirect_response=False)
        self.verify.assert_called_once_with(
            TURNSTILE_URL, data={"secret": "secret-key", "response": "test-token"},
            timeout=(3, 5), allow_redirects=False,
        )
        message, = mail.outbox
        self.assertEqual(message.to, ["formular@example.com"])
        self.assertEqual(message.from_email, "odesilatel@example.com")
        self.assertEqual(message.reply_to, ["jana@example.com"])
        self.assertIn("§6 – elektrotechnik", message.subject)
        self.assertIn(self.data["message"], message.body)
        self.assertContains(client.get(response.url), "vaše zpráva byla odeslána")
        self.assertNotContains(client.get(response.url), "vaše zpráva byla odeslána")

    def test_invalid_fields_are_preserved_and_never_reach_captcha(self):
        response = self.client.post(self.url, {**self.data, "topic": "podvrzeny", "email": "spatne"})
        self.assertEqual(set(response.context["contact_form"].errors), {"topic", "email"})
        self.assertContains(response, self.data["message"], status_code=400)
        self.assertContains(response, 'value="spatne"', status_code=400)
        self.verify.assert_not_called()
        self.assertFalse(mail.outbox)

    def test_missing_or_oversized_token_never_reaches_captcha(self):
        for token in ("", "a" * 2049):
            with self.subTest(token_length=len(token)):
                response = self.client.post(self.url, {**self.data, "cf-turnstile-response": token})
                self.assertContains(response, "CAPTCHA", status_code=400)
        self.verify.assert_not_called()
        self.assertFalse(mail.outbox)

    def test_invalid_and_expired_or_replayed_tokens_are_rejected(self):
        for code, message in (
            ("invalid-input-response", "Ověření CAPTCHA se nezdařilo"),
            ("timeout-or-duplicate", "vypršelo nebo už bylo použito"),
        ):
            with self.subTest(code=code):
                self.verify.return_value.json.return_value = {"success": False, "error-codes": [code]}
                self.assertContains(self.client.post(self.url, self.data), message, status_code=400)
        self.assertFalse(mail.outbox)

    def test_hostname_and_action_must_match(self):
        valid = self.verify.return_value.json.return_value
        for mismatch in ({"hostname": "jiny.example.com"}, {"action": "other"}):
            with self.subTest(mismatch=mismatch):
                self.verify.return_value.json.return_value = {**valid, **mismatch}
                self.assertContains(
                    self.client.post(self.url, self.data), "Ověření CAPTCHA se nezdařilo", status_code=400,
                )
        self.assertFalse(mail.outbox)

    def test_verification_service_outage_or_malformed_response_fails_closed(self):
        self.verify.side_effect = requests.Timeout
        response = self.client.post(self.url, self.data)
        self.assertContains(response, "Ověření CAPTCHA je dočasně nedostupné", status_code=503)
        self.assertContains(response, self.data["message"], status_code=503)
        self.verify.side_effect = None
        self.verify.return_value.json.return_value = []
        self.assertContains(
            self.client.post(self.url, self.data), "Ověření CAPTCHA je dočasně nedostupné", status_code=503,
        )
        self.assertFalse(mail.outbox)

    def test_smtp_failure_or_zero_sends_preserves_input_and_does_not_claim_success(self):
        with patch(
            "courses.emails.transport.EmailMultiAlternatives.send",
            side_effect=[SMTPException("SMTP refused"), 0],
        ) as send, self.assertLogs("courses.contact", level="WARNING"):
            for _ in range(2):
                response = self.client.post(self.url, self.data)
                self.assertContains(response, "Zprávu se nepodařilo odeslat", status_code=503)
                self.assertContains(response, self.data["message"], status_code=503)
                self.assertNotContains(response, "vaše zpráva byla odeslána", status_code=503)
            self.assertEqual(send.call_count, 2)
        self.assertFalse(mail.outbox)
        self.assertNotContains(self.client.get(self.url), "vaše zpráva byla odeslána")

    def test_email_rate_limit_is_shared_across_clients_and_ip_addresses(self):
        self.verify.return_value.json.return_value = {
            "success": False, "error-codes": ["invalid-input-response"],
        }
        for attempt in range(6):
            response = Client().post(
                self.url, self.data, REMOTE_ADDR=f"192.0.2.{attempt}",
            )
            self.assertEqual(response.status_code, 400 if attempt < 5 else 429)
        self.assertEqual(self.verify.call_count, 5)
        self.assertEqual(
            self.client.post(self.url, {**self.data, "email": "other@example.com"}).status_code, 400,
        )

    def test_address_rate_limit_ignores_forwarded_headers(self):
        for attempt in range(31):
            response = Client().post(
                self.url, {**self.data, "cf-turnstile-response": "", "email": f"v{attempt}@example.com"},
                headers={"X-Forwarded-For": f"192.0.2.{attempt}"},
            )
            self.assertEqual(response.status_code, 400 if attempt < 30 else 429)
        self.verify.assert_not_called()

    @override_settings(EMAIL_TEST_RECIPIENTS=("other@example.com",))
    def test_contact_requires_configured_actual_delivery(self):
        self.assertNotContains(self.client.get(self.url), "challenges.cloudflare.com")
        self.assertContains(self.client.post(self.url, self.data), "dočasně nedostupný", status_code=503)
        self.verify.assert_not_called()
        self.assertFalse(mail.outbox)
