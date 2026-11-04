from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import patch

from django.db import close_old_connections
from django.test import RequestFactory, TransactionTestCase
from django.urls import reverse

from courses import views
from courses.models import CustomUser, Course, Question, Choice, QuizAttempt, QuizAttemptQuestion
from courses.quiz_state import serialized_quiz_attempt


class QuizConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="concurrent", is_paid=True)
        self.course = Course.objects.create(title="§4", description="Test", video_url="https://example.invalid")
        self.question = Question.objects.create(course=self.course, text="Question")
        self.correct = Choice.objects.create(question=self.question, text="Correct", is_correct=True)
        self.wrong = Choice.objects.create(question=self.question, text="Wrong")
        self.attempt = QuizAttempt.objects.create(user=self.user, course=self.course, total_questions=1)
        self.aq = QuizAttemptQuestion.objects.create(attempt=self.attempt, question=self.question, order=1)

    def request(self, view, data, **kwargs):
        req = RequestFactory().post("/test/", data)
        req.user = self.user
        return view(req, attempt_id=self.attempt.pk, **kwargs)

    def worker(self, barrier, choice):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return self.request(views.quiz_submit, {
                "current_question_id":self.aq.pk, "choice":choice,
            }).status_code
        finally:
            close_old_connections()

    def test_simultaneous_submit_has_one_immutable_result_and_one_completion(self):
        barrier = Barrier(2)
        with patch("courses.views.process_quiz_completion", return_value=SimpleNamespace(errors=())) as complete:
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs=[pool.submit(self.worker, barrier, self.correct.pk) for _ in range(2)]
                self.assertEqual([j.result(timeout=15) for j in jobs], [302,302])
            self.attempt.refresh_from_db()
            self.assertTrue(self.attempt.passed)
            self.assertEqual(self.attempt.correct_answers, 1)
            complete.assert_called_once()
            when = self.attempt.submitted_at
            self.request(views.quiz_submit, {"current_question_id":self.aq.pk, "choice":self.wrong.pk})
            self.attempt.refresh_from_db();self.aq.refresh_from_db()
            self.assertEqual(self.attempt.submitted_at, when)
            self.assertEqual(self.aq.selected_choice_id, self.correct.pk)
            complete.assert_called_once()

    def test_conflicting_simultaneous_submits_keep_the_winners_answer(self):
        barrier=Barrier(2)
        with patch("courses.views.process_quiz_completion", return_value=SimpleNamespace(errors=())) as complete:
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs=[pool.submit(self.worker,barrier,c.pk) for c in [self.correct,self.wrong]]
                self.assertEqual([j.result(timeout=15) for j in jobs], [302,302])
            self.attempt.refresh_from_db();self.aq.refresh_from_db()
            self.assertEqual(self.attempt.passed,self.aq.selected_choice_id==self.correct.pk)
            self.assertEqual(complete.call_count, 1 if self.attempt.passed else 0)

    def test_delayed_answer_requests_cannot_mutate_submitted_attempt(self):
        # Hold the same lock as submission until an answer writer has started.
        started=Event()
        def writer(view, data, kwargs):
            close_old_connections()
            try:
                started.set()
                return self.request(view,data,**kwargs).status_code
            finally:close_old_connections()
        for view,data,kwargs in [
            (views.quiz_question,{"choice":self.wrong.pk,"next":"1"},{"order":1}),
            (views.quiz_attempt,{f"question_{self.aq.pk}":self.wrong.pk},{}),
        ]:
            with self.subTest(endpoint=view.__name__):
                started.clear()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with serialized_quiz_attempt(self.attempt.pk,self.user) as locked:
                        future=pool.submit(writer,view,data,kwargs)
                        self.assertTrue(started.wait(timeout=5))
                        self.aq.selected_choice=self.correct;self.aq.save()
                        locked.status="submitted";locked.passed=True;locked.save()
                    self.assertEqual(future.result(timeout=15),302)
                self.aq.refresh_from_db()
                self.assertEqual(self.aq.selected_choice_id,self.correct.pk)
