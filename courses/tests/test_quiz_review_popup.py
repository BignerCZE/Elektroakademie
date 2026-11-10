from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import QuizAttempt
from courses.tests.test_quiz import QuizTestBase


class QuizReviewPopupTests(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.attempt = self.create_active_attempt()
        self.attempt.status = QuizAttempt.STATUS_SUBMITTED
        self.attempt.save(update_fields=['status'])

    def test_fragment_contains_review_without_page_shell_and_has_navigation(self):
        for number in (1, 2, 3):
            response = self.client.get(reverse('quiz_attempt_detail', args=[self.attempt.pk, number]), {'fragment': '1'})
            self.assertEqual(response['X-Quiz-Review-Fragment'], '1')
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, '<html')
            self.assertNotContains(response, 'class="topbar')
            self.assertContains(response, f'Otázka {number} z 3')
            self.assertContains(response, 'data-portal-review')
            self.assertContains(response, 'Zpět na historii testů')
            if number == 1:
                self.assertNotContains(response, 'Předchozí otázka')
            if number == 3:
                self.assertNotContains(response, 'Další otázka')

    def test_fragment_checks_ownership_and_submission(self):
        other = get_user_model().objects.create_user(username='other', password='Password123')
        self.client.force_login(other)
        url = reverse('quiz_attempt_detail', args=[self.attempt.pk, 1])
        self.assertEqual(self.client.get(url, {'fragment': '1'}).status_code, 404)
        self.client.force_login(self.user)
        self.attempt.status = QuizAttempt.STATUS_IN_PROGRESS
        self.attempt.save(update_fields=['status'])
        self.assertEqual(self.client.get(url, {'fragment': '1'}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url, {'fragment': '1'}).status_code, 302)

    def test_direct_page_stays_available(self):
        response = self.client.get(reverse('quiz_attempt_detail', args=[self.attempt.pk, 1]))
        self.assertContains(response, 'class="topbar')
        self.assertNotIn('X-Quiz-Review-Fragment', response)
        self.assertContains(response, 'Zpět na přehled testů')
