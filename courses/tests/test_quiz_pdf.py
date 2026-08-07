from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import (
    Choice,
    Course,
    Order,
    OrderParticipant,
    Question,
    QuizAttempt,
    QuizAttemptQuestion,
)
from courses.services import generate_quiz_result_pdf


User = get_user_model()


class QuizResultPdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jan@example.com",
            email="jan@example.com",
            password="Testheslo1",
            first_name="Jan",
            last_name="Novák",
        )

        self.course = Course.objects.create(
            title="§4 – osoba poučená",
            description="Testovací kurz",
            video_url="https://example.com/video",
        )

        self.order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email="jan@example.com",
            registration_number="EA-04-202608-00001",
        )

        self.question = Question.objects.create(
            course=self.course,
            text="Která odpověď je správná?",
        )

        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="Správná odpověď",
            is_correct=True,
        )

        self.wrong_choice = Choice.objects.create(
            question=self.question,
            text="Chybná odpověď",
            is_correct=False,
        )

        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=1,
            correct_answers=1,
            score_percent=100,
            passed=True,
        )

        QuizAttemptQuestion.objects.create(
            attempt=self.attempt,
            question=self.question,
            selected_choice=self.correct_choice,
            order=1,
        )

    def test_generate_quiz_result_pdf_returns_pdf_bytes(self):
        pdf = generate_quiz_result_pdf(
            self.attempt
        )

        self.assertIsInstance(
            pdf,
            bytes,
        )

        self.assertTrue(
            pdf.startswith(b"%PDF")
        )

        self.assertGreater(
            len(pdf),
            1000,
        )

    def test_unsubmitted_attempt_cannot_generate_pdf(self):
        self.attempt.status = QuizAttempt.STATUS_IN_PROGRESS
        self.attempt.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            generate_quiz_result_pdf(
                self.attempt
            )

    def test_failed_attempt_cannot_generate_pdf(self):
        self.attempt.passed = False
        self.attempt.save(update_fields=["passed"])

        with self.assertRaises(ValueError):
            generate_quiz_result_pdf(
                self.attempt
            )

    def test_pdf_view_returns_pdf_for_owner(self):
        self.client.force_login(
            self.user
        )

        response = self.client.get(
            reverse(
                "quiz_result_pdf",
                kwargs={
                    "attempt_id": self.attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )

        self.assertTrue(
            response.content.startswith(b"%PDF")
        )

    def test_pdf_view_is_not_available_to_other_user(self):
        other_user = User.objects.create_user(
            username="petr@example.com",
            email="petr@example.com",
            password="Testheslo1",
        )

        self.client.force_login(
            other_user
        )

        response = self.client.get(
            reverse(
                "quiz_result_pdf",
                kwargs={
                    "attempt_id": self.attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_pdf_view_rejects_failed_attempt(self):
        self.attempt.passed = False
        self.attempt.save(update_fields=["passed"])

        self.client.force_login(
            self.user
        )

        response = self.client.get(
            reverse(
                "quiz_result_pdf",
                kwargs={
                    "attempt_id": self.attempt.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )