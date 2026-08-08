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


class QuizAttemptAdminDetailTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="quiz-admin@example.com",
            email="quiz-admin@example.com",
            password="Testheslo1",
        )

        self.participant_user = User.objects.create_user(
            username="participant@example.com",
            email="participant@example.com",
            first_name="Jan",
            last_name="Novák",
            password="Testheslo1",
            is_paid=True,
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
            company_name="Test s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
        )

        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.participant_user,
            first_name="Jan",
            last_name="Novák",
            email="participant@example.com",
            registration_number="EA-04-202608-00001",
        )

        self.attempt = QuizAttempt.objects.create(
            user=self.participant_user,
            course=self.course,
            attempt_number=1,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=10,
            correct_answers=8,
            score_percent=80,
            passed=True,
        )

        self.client.force_login(
            self.superuser
        )

    def test_quiz_attempt_change_page_is_available(self):
        response = self.client.get(
            reverse(
                "admin:courses_quizattempt_change",
                args=[self.attempt.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_quiz_attempt_change_page_contains_work_dashboard(self):
        response = self.client.get(
            reverse(
                "admin:courses_quizattempt_change",
                args=[self.attempt.pk],
            )
        )

        self.assertContains(
            response,
            "Pracovní souhrn",
        )
        self.assertContains(
            response,
            "Pokus testu",
        )
        self.assertContains(
            response,
            "Jan Novák",
        )
        self.assertContains(
            response,
            "EA-04-202608-00001",
        )
        self.assertContains(
            response,
            "Splněn",
        )
        self.assertContains(
            response,
            "80.00 %",
        )

    def test_quiz_attempt_dashboard_links_to_participant(self):
        response = self.client.get(
            reverse(
                "admin:courses_quizattempt_change",
                args=[self.attempt.pk],
            )
        )

        participant_url = reverse(
            "admin:courses_orderparticipant_change",
            args=[self.participant.pk],
        )

        self.assertContains(
            response,
            participant_url,
        )

    def test_get_participant_prefers_latest_participation(self):
        newer_order = Order.objects.create(
            course_type="4",
            total_price=990,
            status="paid",
            company_name="Novější objednávka s.r.o.",
            street="Nová 2",
            city="Brno",
            zip_code="60200",
        )

        newer_participant = OrderParticipant.objects.create(
            order=newer_order,
            user=self.participant_user,
            first_name="Jan",
            last_name="Novák",
            email="participant@example.com",
            registration_number="EA-04-202608-00002",
        )

        model_admin = admin.site._registry[QuizAttempt]

        selected_participant = model_admin.get_participant(
            self.attempt
        )

        self.assertEqual(
            selected_participant,
            newer_participant,
        )
