from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from courses.models import (
    Course,
    Order,
    OrderParticipant,
    QuizAttempt,
)
from courses.services import generate_certificate


User = get_user_model()


@override_settings(
    TIME_ZONE="Europe/Prague",
    USE_TZ=True,
)
class CertificateValidityTimezoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="timezone@example.com",
            email="timezone@example.com",
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
            paid_at=timezone.now(),
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
            contact_email="kontakt@example.com",
        )
        self.participant = OrderParticipant.objects.create(
            order=self.order,
            user=self.user,
            first_name="Jan",
            last_name="Novák",
            email=self.user.email,
            registration_number="EA-04-202608-00003",
            activation_completed_at=timezone.now(),
        )

    def test_validity_uses_local_issue_date_around_midnight(self):
        submitted_at = datetime(
            2026,
            8,
            8,
            23,
            30,
            tzinfo=dt_timezone.utc,
        )

        attempt = QuizAttempt.objects.create(
            user=self.user,
            course=self.course,
            attempt_number=1,
            status=QuizAttempt.STATUS_SUBMITTED,
            total_questions=10,
            correct_answers=8,
            score_percent=80,
            passed=True,
            submitted_at=submitted_at,
        )

        certificate, created = generate_certificate(attempt)

        self.assertTrue(created)
        self.assertEqual(
            timezone.localtime(
                certificate.issued_at
            ).date().isoformat(),
            "2026-08-09",
        )
        self.assertEqual(
            certificate.valid_until.isoformat(),
            "2029-08-08",
        )
