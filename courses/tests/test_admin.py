from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import (
    Certificate,
    Course,
    Order,
    OrderParticipant,
    Payment,
    Question,
    QuestionCategory,
    QuizAttempt,
)


User = get_user_model()


class AdminAccessTests(TestCase):
    def setUp(self):
        self.normal_user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="Testheslo1",
        )

        self.staff_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Testheslo1",
            is_staff=True,
        )

        self.superuser = User.objects.create_superuser(
            username="superadmin@example.com",
            email="superadmin@example.com",
            password="Testheslo1",
        )

    def test_anonymous_user_cannot_open_admin(self):
        response = self.client.get(
            reverse("admin:index")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse("admin:login"),
            response.url,
        )

    def test_normal_user_cannot_open_admin(self):
        self.client.force_login(
            self.normal_user
        )

        response = self.client.get(
            reverse("admin:index")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            reverse("admin:login"),
            response.url,
        )

    def test_staff_user_can_open_admin(self):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            reverse("admin:index")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_superuser_can_open_admin(self):
        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse("admin:index")
        )

        self.assertEqual(
            response.status_code,
            200,
        )


class AdminRegistrationTests(TestCase):
    def test_custom_user_is_registered(self):
        self.assertIn(
            User,
            admin.site._registry,
        )

    def test_course_is_registered(self):
        self.assertIn(
            Course,
            admin.site._registry,
        )

    def test_question_category_is_registered(self):
        self.assertIn(
            QuestionCategory,
            admin.site._registry,
        )

    def test_question_is_registered(self):
        self.assertIn(
            Question,
            admin.site._registry,
        )

    def test_payment_is_registered(self):
        self.assertIn(
            Payment,
            admin.site._registry,
        )

    def test_order_is_registered(self):
        self.assertIn(
            Order,
            admin.site._registry,
        )

    def test_order_participant_is_registered(self):
        self.assertIn(
            OrderParticipant,
            admin.site._registry,
        )

    def test_quiz_attempt_is_registered(self):
        self.assertIn(
            QuizAttempt,
            admin.site._registry,
        )

    def test_certificate_is_registered(self):
        self.assertIn(
            Certificate,
            admin.site._registry,
        )


class AdminPageTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin@example.com",
            email="superadmin@example.com",
            password="Testheslo1",
        )

        self.client.force_login(
            self.superuser
        )

    def test_order_participant_changelist_is_available(self):
        response = self.client.get(
            reverse(
                "admin:courses_orderparticipant_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_quiz_attempt_changelist_is_available(self):
        response = self.client.get(
            reverse(
                "admin:courses_quizattempt_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_certificate_changelist_is_available(self):
        response = self.client.get(
            reverse(
                "admin:courses_certificate_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )