from django.urls import reverse
from courses.models import QuizAttempt
from courses.tests.test_quiz import QuizTestBase


class QuizReviewTests(QuizTestBase):
    def test_first_middle_last_and_in_progress_protection(self):
        attempt = self.create_active_attempt()
        # The active attempt must remain inaccessible through the review route.
        self.assertEqual(self.client.get(reverse('quiz_attempt_detail', args=[attempt.pk, 1])).status_code, 404)
        attempt.status = QuizAttempt.STATUS_SUBMITTED
        attempt.save(update_fields=['status'])
        for position in (1, 2, 3):
            response = self.client.get(reverse('quiz_attempt_detail', args=[attempt.pk, position]))
            self.assertContains(response, 'Paragraf §4')
            if position > 1:
                self.assertContains(response, 'Předchozí otázka')
                self.assertContains(response, reverse('quiz_attempt_detail', args=[attempt.pk, position-1]))
            else:
                self.assertNotContains(response, 'Předchozí otázka')
            if position < 3:
                self.assertContains(response, 'Další otázka')
                self.assertContains(response, reverse('quiz_attempt_detail', args=[attempt.pk, position+1]))
            else:
                self.assertNotContains(response, 'Další otázka')
            self.assertEqual(response.content.decode().count('button-primary quiz-review-navigation'), 2 if position == 2 else 1)
