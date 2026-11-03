import json
from types import SimpleNamespace
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, TestCase, override_settings
from courses.consent import COOKIE, cookie_context, preferences
from courses.models import CookieConsent


class CookieConsentTests(TestCase):
    def save(self, analytics=False, media=False):
        return self.client.post('/cookies/souhlas/', json.dumps({'analytics': analytics, 'media': media}), content_type='application/json')

    def test_default_is_disabled(self):
        self.assertIsNone(preferences(RequestFactory().get('/')))

    def test_signed_choice_and_audit(self):
        response = self.save(True, False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies[COOKIE]['httponly'])
        self.assertEqual(response.cookies[COOKIE]['samesite'], 'Lax')
        self.assertTrue(preferences(self.client.get('/cookies/').wsgi_request)['analytics'])
        self.assertEqual(CookieConsent.objects.count(), 1)

    def test_withdrawal_preserves_identifier(self):
        self.save(True, True)
        first = CookieConsent.objects.first().identifier
        self.save()
        self.assertEqual(set(CookieConsent.objects.values_list('identifier', flat=True)), {first})
        self.assertFalse(preferences(self.client.get('/cookies/').wsgi_request)['analytics'])

    def test_invalid_payload_does_not_record_consent(self):
        for payload in ['[]', '{}', '{"analytics":"yes","media":true}', 'broken']:
            response = self.client.post('/cookies/souhlas/', payload, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(CookieConsent.objects.exists())

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/cookies/souhlas/', '{}', content_type='application/json').status_code, 403)
        page = client.get('/cookies/')
        self.assertEqual(page.status_code, 200)
        response = client.post('/cookies/souhlas/', json.dumps({'analytics':False,'media':True}), content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200)

    def test_tampered_cookie_is_rejected(self):
        request = RequestFactory().get('/', HTTP_COOKIE='ea_consent=forged')
        self.assertIsNone(preferences(request))

    @override_settings(GA4_MEASUREMENT_ID='G-TEST123')
    def test_private_pages_never_receive_measurement_id(self):
        for name in ['participant_activation', 'quiz_attempt', 'dashboard', 'profile', 'password_reset_confirm']:
            request = RequestFactory().get('/')
            request.resolver_match = SimpleNamespace(url_name=name)
            request.user = AnonymousUser()
            request.session = {}
            self.assertEqual(cookie_context(request)['cookie_config']['measurementId'], '')

    @override_settings(GA4_MEASUREMENT_ID='G-TEST123')
    def test_staff_not_tracked(self):
        request = RequestFactory().get('/')
        request.resolver_match = SimpleNamespace(url_name='index')
        request.user = SimpleNamespace(is_staff=True)
        request.session = {}
        self.assertEqual(cookie_context(request)['cookie_config']['measurementId'], '')

    def test_thumbnail_is_local(self):
        response = self.client.get('/')
        self.assertContains(response, '/static/courses/img/video-thumbnail.jpg')
        self.assertNotContains(response, 'https://i.ytimg.com')
