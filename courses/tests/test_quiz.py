from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import (
    Choice,
    Course,
    EmailLog,
    Question,
    QuestionCategory,
    QuizAttempt,
    QuizAttemptQuestion,
)

User = get_user_model()


@override_settings(
    QUIZ_CATEGORY_COUNTS=[
        ("obecne", 2),
        ("zdravotni", 1),
    ]
)
class QuizTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="Testheslo1",
            is_paid=True,
        )

        self.course = Course.objects.create(
            title="§4 – osoba poučená",
            description="Testovací kurz",
            video_url="https://example.com/video",
        )

        self.category_general = QuestionCategory.objects.create(
            course=self.course,
            name="Obecné",
            slug="obecne",
            questions_per_quiz=2,
            order=1,
        )

        self.category_health = QuestionCategory.objects.create(
            course=self.course,
            name="Zdravotní",
            slug="zdravotni",
            questions_per_quiz=1,
            order=2,
        )

        self.question_1 = self.create_question(
            category=self.category_general,
            text="Obecná otázka 1",
        )
        self.question_2 = self.create_question(
            category=self.category_general,
            text="Obecná otázka 2",
        )
        self.question_3 = self.create_question(
            category=self.category_health,
            text="Zdravotní otázka 1",
        )

        self.client.force_login(self.user)

    def create_question(self, category, text):
        question = Question.objects.create(
            course=self.course,
            category=category,
            text=text,
        )

        correct_choice = Choice.objects.create(
            question=question,
            text="Správná odpověď",
            is_correct=True,
        )

        wrong_choice = Choice.objects.create(
            question=question,
            text="Špatná odpověď",
            is_correct=False,
        )

        question.correct_choice = correct_choice
        question.wrong_choice = wrong_choice

        return question

    def start_quiz(self):
        return self.client.get(
            reverse(
                "quiz_start",
                kwargs={"course_id": self.course.id},
            )
        )

    def create_active_attempt(self):
        attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            total_questions=3,
        )

        questions = [
            self.question_1,
            self.question_2,
            self.question_3,
        ]

        for order, question in enumerate(
            questions,
            start=1,
        ):
            QuizAttemptQuestion.objects.create(
                attempt=attempt,
                question=question,
                order=order,
            )

        return attempt


class QuizTests(QuizTestBase):
    def test_unpaid_user_cannot_start_quiz(self):
        self.user.is_paid = False
        self.user.save(update_fields=["is_paid"])

        response = self.start_quiz()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "buy_course",
                kwargs={"course_id": self.course.id},
            ),
        )

        self.assertEqual(
            QuizAttempt.objects.count(),
            0,
        )

    def test_quiz_start_creates_attempt(self):
        response = self.start_quiz()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            QuizAttempt.objects.count(),
            1,
        )

        attempt = QuizAttempt.objects.get()

        self.assertEqual(
            attempt.user,
            self.user,
        )
        self.assertEqual(
            attempt.course,
            self.course,
        )
        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )
        self.assertEqual(
            attempt.attempt_number,
            1,
        )
        self.assertEqual(
            attempt.total_questions,
            3,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
        )

    def test_quiz_start_creates_correct_questions(self):
        self.start_quiz()

        attempt = QuizAttempt.objects.get()

        attempt_questions = list(
            attempt.attempt_questions
            .select_related(
                "question",
                "question__category",
            )
            .order_by("order")
        )

        self.assertEqual(
            len(attempt_questions),
            3,
        )

        self.assertEqual(
            [item.order for item in attempt_questions],
            [1, 2, 3],
        )

        selected_question_ids = {
            item.question_id
            for item in attempt_questions
        }

        expected_question_ids = {
            self.question_1.id,
            self.question_2.id,
            self.question_3.id,
        }

        self.assertEqual(
            selected_question_ids,
            expected_question_ids,
        )

        category_slugs = [
            item.question.category.slug
            for item in attempt_questions
        ]

        self.assertEqual(
            category_slugs.count("obecne"),
            2,
        )
        self.assertEqual(
            category_slugs.count("zdravotni"),
            1,
        )

    def test_quiz_is_not_created_when_category_has_too_few_questions(
        self,
    ):
        self.question_3.delete()

        response = self.start_quiz()

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertContains(
            response,
            "není dostatek otázek",
            status_code=400,
        )

        self.assertEqual(
            QuizAttempt.objects.count(),
            0,
        )

    def test_existing_active_attempt_is_reused(self):
        attempt = self.create_active_attempt()

        first_question = attempt.attempt_questions.get(
            order=1
        )

        first_question.selected_choice = (
            self.question_1.correct_choice
        )
        first_question.save(
            update_fields=["selected_choice"]
        )

        response = self.start_quiz()

        self.assertEqual(
            QuizAttempt.objects.count(),
            1,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 2,
                },
            ),
        )

    def test_new_attempt_number_increments(self):
        QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            total_questions=3,
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=2,
            total_questions=3,
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        self.start_quiz()

        new_attempt = QuizAttempt.objects.get(
            status=QuizAttempt.STATUS_IN_PROGRESS
        )

        self.assertEqual(
            new_attempt.attempt_number,
            3,
        )

    def test_answer_is_saved_and_next_question_is_opened(self):
        attempt = self.create_active_attempt()

        attempt_question = attempt.attempt_questions.get(
            order=1
        )

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
            {
                "choice": self.question_1.correct_choice.id,
                "next": "1",
            },
        )

        attempt_question.refresh_from_db()

        self.assertEqual(
            attempt_question.selected_choice,
            self.question_1.correct_choice,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 2,
                },
            ),
        )

    def test_choice_from_another_question_is_not_saved(self):
        attempt = self.create_active_attempt()

        attempt_question = attempt.attempt_questions.get(
            order=1
        )

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
            {
                "choice": self.question_2.correct_choice.id,
                "next": "1",
            },
        )

        attempt_question.refresh_from_db()

        self.assertIsNone(
            attempt_question.selected_choice
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 2,
                },
            ),
        )

    def test_previous_opens_previous_question(self):
        attempt = self.create_active_attempt()

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 2,
                },
            ),
            {
                "previous": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
        )

    def test_go_to_is_limited_to_existing_question_range(self):
        attempt = self.create_active_attempt()

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
            {
                "go_to": "999",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 3,
                },
            ),
        )

    def test_leave_test_keeps_attempt_in_progress(self):
        attempt = self.create_active_attempt()

        response = self.client.post(
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 1,
                },
            ),
            {
                "leave_test": "1",
            },
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )

        self.assertIsNone(
            attempt.submitted_at
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz",
                kwargs={
                    "course_id": self.course.id,
                },
            ),
        )


@override_settings(
    QUIZ_PASS_PERCENTAGE=70,
)
class QuizSubmitTests(QuizTestBase):
    def answer_question(
        self,
        attempt,
        order,
        correct=True,
    ):
        attempt_question = attempt.attempt_questions.get(
            order=order
        )

        question = attempt_question.question

        choice = question.choice_set.get(
            is_correct=correct
        )

        attempt_question.selected_choice = choice
        attempt_question.save(
            update_fields=["selected_choice"]
        )

        return attempt_question

    def answer_all(
        self,
        attempt,
        correct_orders=None,
    ):
        if correct_orders is None:
            correct_orders = {1, 2, 3}

        for order in range(1, 4):
            self.answer_question(
                attempt,
                order,
                correct=order in correct_orders,
            )

    def submit_attempt(self, attempt, data=None):
        return self.client.post(
            reverse(
                "quiz_submit",
                kwargs={
                    "attempt_id": attempt.id,
                },
            ),
            data or {},
        )

    def test_quiz_submit_requires_post(self):
        attempt = self.create_active_attempt()

        response = self.client.get(
            reverse(
                "quiz_submit",
                kwargs={
                    "attempt_id": attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )

    def test_unanswered_question_prevents_submission(self):
        attempt = self.create_active_attempt()

        self.answer_question(
            attempt,
            order=1,
            correct=True,
        )
        self.answer_question(
            attempt,
            order=3,
            correct=True,
        )

        response = self.submit_attempt(attempt)

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )
        self.assertIsNone(attempt.submitted_at)

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 2,
                },
            ),
        )

    def test_current_question_answer_can_be_saved_during_submit(
        self,
    ):
        attempt = self.create_active_attempt()

        self.answer_question(
            attempt,
            order=1,
            correct=True,
        )
        self.answer_question(
            attempt,
            order=2,
            correct=True,
        )

        last_attempt_question = (
            attempt.attempt_questions.get(order=3)
        )

        correct_choice = (
            last_attempt_question.question.choice_set.get(
                is_correct=True
            )
        )

        response = self.submit_attempt(
            attempt,
            {
                "current_question_id": (
                    last_attempt_question.id
                ),
                "choice": correct_choice.id,
            },
        )

        last_attempt_question.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            last_attempt_question.selected_choice,
            correct_choice,
        )

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_SUBMITTED,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_successful_quiz_is_evaluated_correctly(self):
        attempt = self.create_active_attempt()

        self.answer_all(attempt)

        response = self.submit_attempt(attempt)

        attempt.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_SUBMITTED,
        )

        self.assertEqual(
            attempt.total_questions,
            3,
        )

        self.assertEqual(
            attempt.correct_answers,
            3,
        )

        self.assertEqual(
            attempt.score_percent,
            Decimal("100.00"),
        )

        self.assertTrue(attempt.passed)

        self.assertIsNotNone(
            attempt.submitted_at
        )

        self.assertTrue(
            self.user.passed_quiz
        )

        expected_url = reverse(
            "quiz_attempt_detail",
            kwargs={
                "attempt_id": attempt.id,
                "order": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            f"{expected_url}?from=result",
        )

    def test_failed_quiz_is_evaluated_correctly(self):
        attempt = self.create_active_attempt()

        self.answer_all(
            attempt,
            correct_orders={1, 2},
        )

        self.submit_attempt(attempt)

        attempt.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_SUBMITTED,
        )

        self.assertEqual(
            attempt.correct_answers,
            2,
        )

        self.assertEqual(
            attempt.score_percent,
            Decimal("66.67"),
        )

        self.assertFalse(
            attempt.passed
        )

        self.assertIsNotNone(
            attempt.submitted_at
        )

        self.assertFalse(
            self.user.passed_quiz
        )

    @override_settings(
        QUIZ_PASS_PERCENTAGE=66.67,
    )
    def test_score_exactly_on_pass_limit_passes(self):
        attempt = self.create_active_attempt()

        self.answer_all(
            attempt,
            correct_orders={1, 2},
        )

        self.submit_attempt(attempt)

        attempt.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(
            attempt.score_percent,
            Decimal("66.67"),
        )

        self.assertTrue(
            attempt.passed
        )

        self.assertTrue(
            self.user.passed_quiz
        )

    def test_submitted_attempt_cannot_be_submitted_again(self):
        attempt = self.create_active_attempt()

        self.answer_all(attempt)

        first_response = self.submit_attempt(
            attempt
        )

        attempt.refresh_from_db()

        original_submitted_at = (
            attempt.submitted_at
        )
        original_score = (
            attempt.score_percent
        )

        self.assertEqual(
            first_response.status_code,
            302,
        )

        second_response = self.submit_attempt(
            attempt
        )

        self.assertEqual(
            second_response.status_code,
            404,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.submitted_at,
            original_submitted_at,
        )

        self.assertEqual(
            attempt.score_percent,
            original_score,
        )

    def test_submit_cannot_save_choice_from_another_question(
        self,
    ):
        attempt = self.create_active_attempt()

        self.answer_question(
            attempt,
            order=1,
            correct=True,
        )

        self.answer_question(
            attempt,
            order=2,
            correct=True,
        )

        last_attempt_question = (
            attempt.attempt_questions.get(
                order=3
            )
        )

        foreign_choice = (
            self.question_1.correct_choice
        )

        response = self.submit_attempt(
            attempt,
            {
                "current_question_id": (
                    last_attempt_question.id
                ),
                "choice": foreign_choice.id,
            },
        )

        last_attempt_question.refresh_from_db()
        attempt.refresh_from_db()

        self.assertIsNone(
            last_attempt_question.selected_choice
        )

        self.assertEqual(
            attempt.status,
            QuizAttempt.STATUS_IN_PROGRESS,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "quiz_question",
                kwargs={
                    "attempt_id": attempt.id,
                    "order": 3,
                },
            ),
        )

    @patch("courses.views.deliver_email")
    @patch("courses.views.build_course_completed_email")
    @patch("courses.views.generate_certificate")
    def test_first_successful_attempt_processes_completion_email(
        self,
        mock_generate_certificate,
        mock_build_email,
        mock_deliver_email,
    ):
        attempt = self.create_active_attempt()
        self.answer_all(attempt)

        certificate = Mock()
        rendered_email = Mock()

        mock_generate_certificate.return_value = (
            certificate,
            True,
        )
        mock_build_email.return_value = rendered_email

        response = self.submit_attempt(
            attempt
        )

        attempt.refresh_from_db()

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertTrue(
            attempt.passed
        )

        mock_generate_certificate.assert_called_once_with(
            attempt
        )
        mock_build_email.assert_called_once_with(
            attempt
        )
        mock_deliver_email.assert_called_once_with(
            rendered_email,
            email_type=EmailLog.TYPE_COURSE_COMPLETED,
            quiz_attempt=attempt,
        )

    @patch("courses.views.deliver_email")
    @patch("courses.views.build_course_completed_email")
    @patch("courses.views.generate_certificate")
    def test_existing_certificate_does_not_process_completion_email(
        self,
        mock_generate_certificate,
        mock_build_email,
        mock_deliver_email,
    ):
        attempt = self.create_active_attempt()
        self.answer_all(attempt)

        certificate = Mock()

        mock_generate_certificate.return_value = (
            certificate,
            False,
        )

        self.submit_attempt(
            attempt
        )

        attempt.refresh_from_db()

        self.assertTrue(
            attempt.passed
        )

        mock_generate_certificate.assert_called_once_with(
            attempt
        )
        mock_build_email.assert_not_called()
        mock_deliver_email.assert_not_called()

    @patch("courses.views.deliver_email")
    @patch("courses.views.build_course_completed_email")
    @patch("courses.views.generate_certificate")
    def test_failed_attempt_does_not_process_completion_email(
        self,
        mock_generate_certificate,
        mock_build_email,
        mock_deliver_email,
    ):
        attempt = self.create_active_attempt()

        self.answer_all(
            attempt,
            correct_orders={1, 2},
        )

        self.submit_attempt(
            attempt
        )

        attempt.refresh_from_db()

        self.assertFalse(
            attempt.passed
        )

        mock_generate_certificate.assert_not_called()
        mock_build_email.assert_not_called()
        mock_deliver_email.assert_not_called()
