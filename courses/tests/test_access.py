from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import (
    Choice,
    Course,
    Question,
    QuestionCategory,
    QuizAttempt,
    QuizAttemptQuestion,
)


User = get_user_model()


class AccessTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title="§4 – osoba poučená",
            description="Testovací kurz",
            video_url="https://example.com/video",
        )

        self.category = QuestionCategory.objects.create(
            course=self.course,
            name="Obecné",
            slug="obecne",
            questions_per_quiz=1,
            order=1,
        )

        self.question = Question.objects.create(
            course=self.course,
            category=self.category,
            text="Testovací otázka",
        )

        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="Správná odpověď",
            is_correct=True,
        )

        self.wrong_choice = Choice.objects.create(
            question=self.question,
            text="Špatná odpověď",
            is_correct=False,
        )

        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="Testheslo1",
            is_paid=True,
        )

        self.other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="Testheslo1",
            is_paid=True,
        )

        self.unpaid_user = User.objects.create_user(
            username="unpaid@example.com",
            email="unpaid@example.com",
            password="Testheslo1",
            is_paid=False,
        )

        self.active_attempt = QuizAttempt.objects.create(
            user=self.owner,
            course=self.course,
            attempt_number=1,
            total_questions=1,
            status=QuizAttempt.STATUS_IN_PROGRESS,
        )

        self.active_attempt_question = (
            QuizAttemptQuestion.objects.create(
                attempt=self.active_attempt,
                question=self.question,
                order=1,
            )
        )

        self.submitted_attempt = QuizAttempt.objects.create(
            user=self.owner,
            course=self.course,
            attempt_number=2,
            total_questions=1,
            correct_answers=1,
            score_percent=100,
            passed=True,
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        self.submitted_attempt_question = (
            QuizAttemptQuestion.objects.create(
                attempt=self.submitted_attempt,
                question=self.question,
                selected_choice=self.correct_choice,
                order=1,
            )
        )

    def assert_redirects_to_login(self, response):
        self.assertEqual(
            response.status_code,
            302,
        )

        login_url = reverse("login")

        self.assertTrue(
            response.url.startswith(
                f"{login_url}?next="
            )
        )

    def test_anonymous_user_cannot_open_dashboard(self):
        response = self.client.get(
            reverse("dashboard")
        )

        self.assert_redirects_to_login(response)

    def test_anonymous_user_cannot_open_profile(self):
        response = self.client.get(
            reverse("profile")
        )

        self.assert_redirects_to_login(response)

    def test_anonymous_user_cannot_open_video(self):
        response = self.client.get(
            reverse(
                "video_detail",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assert_redirects_to_login(response)

    def test_anonymous_user_cannot_open_quiz_dashboard(self):
        response = self.client.get(
            reverse(
                "quiz",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assert_redirects_to_login(response)

    def test_unpaid_user_cannot_open_video(self):
        self.client.force_login(
            self.unpaid_user
        )

        response = self.client.get(
            reverse(
                "video_detail",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "buy_course",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
        )

    def test_unpaid_user_cannot_open_quiz_dashboard(self):
        self.client.force_login(
            self.unpaid_user
        )

        response = self.client.get(
            reverse(
                "quiz",
                kwargs={
                    "course_id": self.course.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "buy_course",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
        )

    def test_other_user_cannot_open_active_attempt_question(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.get(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": self.active_attempt.id,
                    "order": 1,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_user_cannot_change_active_attempt_answer(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": self.active_attempt.id,
                    "order": 1,
                },
            ),
            {
                "choice": self.correct_choice.id,
                "next": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.active_attempt_question.refresh_from_db()

        self.assertIsNone(
            self.active_attempt_question.selected_choice
        )

    def test_other_user_cannot_open_active_attempt(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.get(
            reverse(
                "quiz_attempt",
                kwargs={
                    "attempt_id": self.active_attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_user_cannot_submit_active_attempt(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.post(
            reverse(
                "quiz_submit",
                kwargs={
                    "attempt_id": self.active_attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.active_attempt.refresh_from_db()

        self.assertEqual(
            self.active_attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )

        self.assertIsNone(
            self.active_attempt.submitted_at
        )

    def test_other_user_cannot_open_submitted_attempt_result(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.get(
            reverse(
                "quiz_result",
                kwargs={
                    "attempt_id": self.submitted_attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_user_cannot_open_submitted_attempt_detail(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.get(
            reverse(
                "quiz_attempt_detail",
                kwargs={
                    "attempt_id": self.submitted_attempt.id,
                    "order": 1,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_dashboard_contains_only_current_users_attempts(self):
        own_attempt = QuizAttempt.objects.create(
            user=self.other_user,
            course=self.course,
            attempt_number=1,
            total_questions=1,
            correct_answers=0,
            score_percent=0,
            passed=False,
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        self.client.force_login(
            self.other_user
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["submitted_attempts_count"],
            1,
        )

        self.assertEqual(
            response.context["latest_attempt"],
            own_attempt,
        )

        self.assertNotEqual(
            response.context["latest_attempt"],
            self.submitted_attempt,
        )