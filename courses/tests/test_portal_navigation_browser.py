"""Run with a usable Playwright Chromium installation; no SMTP is used."""
import os
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections
from unittest.mock import patch
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright, expect, Error
from courses.models import Course, Order, OrderParticipant, Question, Choice, QuizAttempt, QuizAttemptQuestion


@override_settings(EMAIL_TRANSPORT='preview')
class PortalNavigationBrowserTests(StaticLiveServerTestCase):
    @staticmethod
    def database_call(operation):
        # Playwright's sync API runs an asyncio loop in the calling thread.
        # Keep all ORM work (including lazy relations) outside that thread.
        def run():
            close_old_connections()
            try:
                return operation()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(run).result()

    def setUp(self):
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        options = {'headless': True, 'ignore_default_args': ['--disable-back-forward-cache']}
        if os.getenv('CHROMIUM_EXECUTABLE_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE_PATH']
        try:
            self.browser = self.playwright.chromium.launch(**options)
        except Error as error:
            if "Executable doesn't exist" in str(error):
                self.skipTest("Install Playwright Chromium to verify browser navigation and mobile layout.")
            raise
        self.addCleanup(self.browser.close)
        self.context = self.browser.new_context(viewport={'width': 1366, 'height': 900})
        self.context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(self.live_server_url) else route.abort())
        self.page = self.context.new_page()
        self.course = self.database_call(lambda: Course.objects.create(
            title='Elektroakademie', description='Test', video_url='https://example.test/video'))

    def activate_through_checkout(self):
        from courses.tests.test_registration import RegistrationTests
        self.page.goto(self.live_server_url + reverse('register'))
        self.page.locator('[data-cookie-choice="none"]').click()
        data = RegistrationTests().get_registration_data()
        data['csrfmiddlewaretoken'] = self.page.locator('[name="csrfmiddlewaretoken"]').first.input_value()
        response = self.context.request.post(self.live_server_url + reverse('register'), form=data)
        self.assertTrue(response.ok)
        order = self.database_call(lambda: Order.objects.get())
        self.page.goto(self.live_server_url + reverse('order_payment_simulation', args=[order.pk]))
        # Exercise the actual countdown and payment workflow; only PDF rendering
        # is stubbed here because this test concerns navigation, not printing.
        with patch('courses.workflows.invoice_pdf', return_value=b'%PDF-navigation-test'):
            self.page.wait_for_url('**' + reverse('order_payment_success', args=[order.pk]), timeout=45000)
            expect(self.page.locator('[data-copy-link]').first).to_be_visible()
        order = self.database_call(lambda: Order.objects.get(pk=order.pk))
        self.assertEqual(order.status, 'paid')
        participant = self.database_call(lambda: OrderParticipant.objects.get(order_id=order.pk))
        activation = reverse('participant_activation', args=[participant.activation_token])
        self.page.goto(self.live_server_url + activation)
        # Use the same validated payload as the server regression, typed into
        # the actual activation form and submitted with its real button.
        values = {'password1':'Testheslo1', 'password2':'Testheslo1',
                  'birth_day':'15', 'birth_month':'5', 'birth_year':'1990',
                  'birth_place':'Praha', 'permanent_address':'Testovací 1, Praha',
                  'employer_name':'Testovací firma s.r.o.', 'employer_ico':'00123456',
                  'employer_address':'Testovací 1, Praha'}
        for name, value in values.items():
            self.page.locator(f'[name="{name}"]').fill(value)
        self.page.get_by_role('button', name='Aktivovat účet').click()
        self.page.wait_for_url('**' + reverse('dashboard'))
        participant = self.database_call(lambda: OrderParticipant.objects.select_related("user").get(pk=participant.pk))
        self.assertIsNotNone(participant.activation_completed_at)
        self.assertTrue(participant.user.is_paid)
        return participant, activation

    def test_browser_back_after_activation_goes_home(self):
        participant, activation = self.activate_through_checkout()
        self.page.go_back()
        self.page.wait_for_url(self.live_server_url + reverse('index'))
        self.page.goto(self.live_server_url + activation)
        self.page.wait_for_url(self.live_server_url + reverse('index'))
        self.page.goto(self.live_server_url + reverse('dashboard'))
        expect(self.page.locator('.sidebar-nav').get_by_role('link', name='Video', exact=True)).to_be_visible()
        self.assertEqual(self.database_call(lambda: OrderParticipant.objects.filter(user_id=participant.user_id).count()), 1)

    def test_review_buttons_at_desktop_and_mobile_sizes(self):
        participant, _ = self.activate_through_checkout()
        def create_review_attempt():
            attempt = QuizAttempt.objects.create(user_id=participant.user_id, course_id=self.course.pk,
                attempt_number=1, total_questions=3, correct_answers=3, score_percent=100,
                passed=True, status=QuizAttempt.STATUS_SUBMITTED, submitted_at=timezone.now())
            for number in range(1, 4):
                question = Question.objects.create(course_id=self.course.pk, text=f'Testovací otázka {number}')
                choice = Choice.objects.create(question=question, text='Ano', is_correct=True)
                QuizAttemptQuestion.objects.create(attempt=attempt, question=question, order=number, selected_choice=choice)
            return attempt.pk

        attempt_id = self.database_call(create_review_attempt)
        for width in (1366, 390, 320):
            self.page.set_viewport_size({'width':width, 'height':900})
            for number in (1, 2, 3):
                self.page.goto(self.live_server_url + reverse('quiz_attempt_detail', args=[attempt_id, number]))
                buttons = self.page.locator('.quiz-review-navigation')
                self.assertEqual(buttons.count(), 2 if number == 2 else 1)
                if number == 2:
                    first, second = buttons.nth(0).bounding_box(), buttons.nth(1).bounding_box()
                    self.assertAlmostEqual(first['width'], second['width'], delta=1)
                    styles = buttons.evaluate_all('(els) => els.map(e => { const s = getComputedStyle(e); return [s.backgroundColor, s.color, s.borderRadius]; })')
                    self.assertEqual(styles[0], styles[1])
                self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
