from unittest.mock import patch
from django.urls import reverse
from courses.models import QuizAttempt
from courses.tests.test_quiz import QuizTestBase


class QuizActivePopupTests(QuizTestBase):
    def test_popup_start_renders_only_the_quiz_and_preserves_mode(self):
        response = self.client.post(reverse('quiz_start', args=[self.course.pk]) + '?popup=1', follow=True)
        self.assertContains(response, 'quiz-popup-body')
        self.assertNotContains(response, 'class="topbar')
        self.assertNotContains(response, 'portal-account-bar')
        self.assertContains(response, '?popup=1')
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_popup_navigation_and_leave_save_answers_without_submission(self):
        attempt = self.create_active_attempt()
        url = reverse('quiz_question', args=[attempt.pk, 1]) + '?popup=1'
        response = self.client.post(url, {'next':'1', 'choice':self.question_1.correct_choice.pk})
        self.assertRedirects(response, reverse('quiz_question', args=[attempt.pk, 2]) + '?popup=1')
        response = self.client.post(reverse('quiz_question', args=[attempt.pk, 2]) + '?popup=1',
                                    {'leave_test':'1', 'choice':self.question_2.correct_choice.pk})
        self.assertContains(response, 'quiz-popup-event')
        self.assertEqual(response.context['quiz_event']['type'], 'ea-quiz-left')
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.STATUS_IN_PROGRESS)
        self.assertIsNotNone(attempt.attempt_questions.get(order=2).selected_choice_id)
        self.assertEqual(QuizAttempt.objects.count(), 1)
        response = self.client.get(reverse('quiz_start', args=[self.course.pk]) + '?popup=1')
        self.assertRedirects(response, reverse('quiz_question', args=[attempt.pk, 3]) + '?popup=1')

    def test_popup_submit_returns_completion_event_with_existing_review(self):
        attempt = self.create_active_attempt()
        for item in attempt.attempt_questions.select_related('question'):
            item.selected_choice = item.question.choice_set.get(is_correct=True)
            item.save(update_fields=['selected_choice'])
        with patch('courses.views.process_quiz_completion') as workflow:
            workflow.return_value.errors = []
            response = self.client.post(reverse('quiz_submit', args=[attempt.pk]) + '?popup=1')
        self.assertEqual(response.context['quiz_event']['type'], 'ea-quiz-completed')
        self.assertIn(reverse('quiz_attempt_detail', args=[attempt.pk, 1]), response.context['quiz_event']['review_url'])
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.STATUS_SUBMITTED)
        self.assertTrue(attempt.passed)

    def test_popup_cannot_read_another_users_attempt(self):
        attempt = self.create_active_attempt()
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username='other', is_paid=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('quiz_question', args=[attempt.pk, 1]) + '?popup=1').status_code, 404)
