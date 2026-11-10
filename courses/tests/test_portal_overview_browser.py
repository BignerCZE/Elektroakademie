"""Browser checks for the unified overview. Needs Playwright Chromium."""
import os
from unittest.mock import patch
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, override_settings
from django.urls import reverse
from playwright.sync_api import sync_playwright, expect, Error
from courses.models import QuizAttempt, Question, Choice, QuizAttemptQuestion


@override_settings(EMAIL_TRANSPORT='preview')
class PortalOverviewBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        # Create fixtures BEFORE Playwright starts its asyncio event loop.
        from courses.tests.test_certificates import CertificateTestBase
        fixture = CertificateTestBase()
        fixture.client = Client()
        fixture.setUp()
        self.certificate, _ = fixture.create_certificate()
        for number in range(1, 4):
            question = Question.objects.create(course=fixture.course, text=f'Kontrolní otázka {number}')
            choice = Choice.objects.create(question=question, text='Správná odpověď', is_correct=True)
            QuizAttemptQuestion.objects.create(attempt=fixture.attempt, question=question,
                                               order=number, selected_choice=choice)
        for number in range(2, 32):
            QuizAttempt.objects.create(user=fixture.user, course=fixture.course,
                attempt_number=number, status=QuizAttempt.STATUS_SUBMITTED,
                passed=False, score_percent=0, submitted_at=fixture.submitted_at)
        self.quiz_user_id = fixture.user.pk
        self.quiz_attempt_id = fixture.attempt.pk
        session_key = fixture.client.session.session_key
        from django.conf import settings
        self.cookie_name = settings.SESSION_COOKIE_NAME
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        options = {'headless': True}
        if os.getenv('CHROMIUM_EXECUTABLE_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE_PATH']
        try:
            self.browser = self.playwright.chromium.launch(**options)
        except Error as error:
            if "Executable doesn't exist" in str(error):
                self.skipTest('Install Playwright Chromium to check the overview layout and dialogs.')
            raise
        self.addCleanup(self.browser.close)
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(self.live_server_url) else route.abort())
        self.context.add_cookies([{'name':self.cookie_name, 'value':session_key, 'url':self.live_server_url}])
        self.page = self.context.new_page()
        self.page.goto(self.live_server_url + reverse('dashboard'))

    def test_video_consent_dialog_close_and_logout(self):
        self.page.locator('[data-cookie-choice="none"]').click()
        video = self.page.get_by_role('button', name='Přehrát výukové video')
        video.click()
        self.assertEqual(self.page.locator('#portal-video-dialog iframe').count(), 0)
        self.page.locator('[data-cookie-choice="all"]').click()
        video.click()
        expect(self.page.locator('#portal-video-dialog')).to_be_visible()
        self.assertIn('J_eSsfNwDVw', self.page.locator('#portal-video-dialog iframe').get_attribute('src'))
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#portal-video-dialog')).not_to_be_visible()
        self.assertEqual(self.page.locator('#portal-video-dialog iframe').count(), 0)
        expect(video).to_be_focused()
        self.page.get_by_role('button', name='Odhlásit se', exact=True).click()
        self.page.wait_for_url(self.live_server_url + reverse('index'))
        self.page.goto(self.live_server_url + reverse('dashboard'))
        self.page.wait_for_url('**/prihlaseni/**')

    def test_responsive_history_logo_and_certificate(self):
        expect(self.page.locator('.portal-account-bar')).to_be_visible()
        self.assertEqual(self.page.locator('.dashboard-shell-sidebar').count(), 0)
        self.page.locator('[data-cookie-choice="none"]').click()
        history_button = self.page.get_by_role('button', name='Historie testů')
        history_dialog = self.page.locator('#portal-history-dialog')
        expect(history_dialog).not_to_be_visible()
        for width, height in ((1920, 1080), (1440, 900), (1366, 768)):
            self.page.set_viewport_size({'width': width, 'height': height})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollHeight'), height + 1)
        for width in (1440, 1024, 768, 390, 320):
            self.page.set_viewport_size({'width':width, 'height':1000})
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
            logo = self.page.locator('.portal-topbar .logo').bounding_box()
            self.assertAlmostEqual(logo['x'] + logo['width']/2, width/2, delta=2)
            history_button.click()
            expect(history_dialog).to_be_visible()
            bounds = history_dialog.bounding_box()
            self.assertAlmostEqual(bounds['x'] + bounds['width']/2, width/2, delta=2)
            self.assertAlmostEqual(bounds['y'] + bounds['height']/2, 500, delta=2)
            history = history_dialog.locator('.portal-test-history')
            self.assertTrue(history.evaluate('(el) => el.scrollHeight > el.clientHeight'))
            before = self.page.evaluate('window.scrollY')
            history.evaluate('(el) => el.scrollTop = 100')
            self.assertGreater(history.evaluate('(el) => el.scrollTop'), 0)
            self.assertEqual(self.page.evaluate('window.scrollY'), before)
            self.page.keyboard.press('Escape')
            expect(history_dialog).not_to_be_visible()
            expect(history_button).to_be_focused()
        self.page.get_by_role('button', name='Náhled certifikátu', exact=True).click()
        dialog = self.page.locator('#portal-certificate-dialog')
        expect(dialog).to_be_visible()
        expect(dialog.locator('.certificate-document')).to_contain_text(self.certificate.certificate_number)
        self.page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
        with patch('courses.views.generate_certificate_pdf', return_value=b'%PDF-browser-download'):
            with self.page.expect_download() as download:
                self.page.get_by_role('link', name='Stáhnout PDF', exact=True).click()
            self.assertTrue(download.value.suggested_filename.endswith('.pdf'))

    def test_review_stays_in_the_history_popup_with_question_navigation(self):
        self.page.locator('[data-cookie-choice="none"]').click()
        dashboard_url = self.page.url
        direct = self.page.get_by_role('link', name='Zobrazit odpovědi', exact=True)
        direct.click()
        dialog = self.page.locator('#portal-history-dialog')
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role('heading', name='Otázka 1 z 3', exact=True)).to_be_visible()
        self.assertEqual(self.page.url, dashboard_url)
        self.assertEqual(dialog.locator('.topbar').count(), 0)
        self.assertEqual(dialog.get_by_role('link', name='Předchozí otázka', exact=True).count(), 0)
        dialog.get_by_role('link', name='Další otázka', exact=True).click()
        expect(dialog.get_by_role('heading', name='Otázka 2 z 3', exact=True)).to_be_visible()
        dialog.get_by_role('link', name='Předchozí otázka', exact=True).click()
        expect(dialog.get_by_role('heading', name='Otázka 1 z 3', exact=True)).to_be_visible()
        dialog.locator('.quiz-question-number').filter(has_text='3').click()
        expect(dialog.get_by_role('heading', name='Otázka 3 z 3', exact=True)).to_be_visible()
        self.assertEqual(dialog.get_by_role('link', name='Další otázka', exact=True).count(), 0)
        self.assertEqual(self.page.url, dashboard_url)
        dialog.get_by_role('button', name='Zpět na historii', exact=True).click()
        expect(dialog.locator('[data-portal-history-list]')).to_be_visible()
        row = dialog.locator('.portal-history-row').filter(has=self.page.get_by_text('Pokus 1', exact=True))
        row.get_by_role('link', name='Zobrazit odpovědi').click()
        expect(dialog.get_by_role('heading', name='Otázka 1 z 3', exact=True)).to_be_visible()
        self.page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
        expect(direct).to_be_focused()
        self.assertEqual(self.page.url, dashboard_url)

    def test_active_quiz_popup_save_resume_submit_and_center(self):
        from courses.tests import test_portal_navigation_browser as helpers
        from django.contrib.auth import get_user_model
        def prepare():
            get_user_model().objects.filter(pk=self.quiz_user_id).update(passed_quiz=False)
            QuizAttempt.objects.filter(pk=self.quiz_attempt_id).update(status=QuizAttempt.STATUS_IN_PROGRESS, submitted_at=None)
            QuizAttemptQuestion.objects.filter(attempt_id=self.quiz_attempt_id).update(selected_choice=None)
        helpers.PortalNavigationBrowserTests.database_call(prepare)
        self.page.locator('[data-cookie-choice="none"]').click()
        self.page.reload()
        self.page.on('dialog', lambda dialog: dialog.accept())
        self.page.get_by_role('link', name='Pokračovat v testu', exact=True).click()
        dialog = self.page.locator('#portal-active-quiz-dialog')
        expect(dialog).to_be_visible()
        bounds = dialog.bounding_box()
        self.assertAlmostEqual(bounds['x'] + bounds['width']/2, 720, delta=2)
        self.assertAlmostEqual(bounds['y'] + bounds['height']/2, 500, delta=2)
        frame = self.page.frame_locator('#portal-active-quiz-frame')
        expect(frame.get_by_role('heading', name='Otázka 1 z 3')).to_be_visible()
        frame.locator('input[type="radio"]').first.check()
        frame.get_by_role('button', name='Další otázka', exact=True).click()
        expect(frame.get_by_role('heading', name='Otázka 2 z 3')).to_be_visible()
        frame.locator('input[type="radio"]').first.check()
        dialog.get_by_role('button', name='Opustit rozpracovaný test').click()
        expect(self.page.get_by_role('link', name='Pokračovat v testu', exact=True)).to_be_visible()
        expect(dialog).not_to_be_visible()
        self.page.get_by_role('link', name='Pokračovat v testu', exact=True).click()
        expect(frame.get_by_role('heading', name='Otázka 3 z 3')).to_be_visible()
        frame.locator('input[type="radio"]').first.check()
        with patch('courses.views.process_quiz_completion') as workflow:
            workflow.return_value.errors = []
            frame.get_by_role('button', name='Odeslat test', exact=True).click()
            history = self.page.locator('#portal-history-dialog')
            expect(history).to_be_visible(timeout=15000)
            expect(history.get_by_role('heading', name='Otázka 1 z 3', exact=True)).to_be_visible()
        expect(self.page.locator('#portal-active-quiz-dialog')).not_to_be_visible()
