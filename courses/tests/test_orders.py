from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from courses.models import (
    Order,
    OrderParticipant,
    RegistrationNumberSequence,
)
from courses.services import (
    generate_registration_number,
    mark_order_as_paid,
)


class RegistrationNumberTests(TestCase):

    @patch("courses.services.timezone.localdate")
    def test_generate_first_registration_number(self, mock_localdate):
        mock_localdate.return_value = date(2026, 8, 7)

        registration_number = generate_registration_number("4")

        self.assertEqual(
            registration_number,
            "EA-04-202608-00001",
        )

        sequence = RegistrationNumberSequence.objects.get(
            course_type="4",
            year=2026,
            month=8,
        )

        self.assertEqual(sequence.last_number, 1)

    @patch("courses.services.timezone.localdate")
    def test_registration_numbers_increment(self, mock_localdate):
        mock_localdate.return_value = date(2026, 8, 7)

        first_number = generate_registration_number("4")
        second_number = generate_registration_number("4")
        third_number = generate_registration_number("4")

        self.assertEqual(
            first_number,
            "EA-04-202608-00001",
        )
        self.assertEqual(
            second_number,
            "EA-04-202608-00002",
        )
        self.assertEqual(
            third_number,
            "EA-04-202608-00003",
        )

        sequence = RegistrationNumberSequence.objects.get(
            course_type="4",
            year=2026,
            month=8,
        )

        self.assertEqual(sequence.last_number, 3)

    @patch("courses.services.timezone.localdate")
    def test_registration_sequences_are_separate_by_course(
        self,
        mock_localdate,
    ):
        mock_localdate.return_value = date(2026, 8, 7)

        course_4_first = generate_registration_number("4")
        course_6_first = generate_registration_number("6")
        course_4_second = generate_registration_number("4")

        self.assertEqual(
            course_4_first,
            "EA-04-202608-00001",
        )
        self.assertEqual(
            course_6_first,
            "EA-06-202608-00001",
        )
        self.assertEqual(
            course_4_second,
            "EA-04-202608-00002",
        )

    @patch("courses.services.timezone.localdate")
    def test_registration_sequences_are_separate_by_month(
        self,
        mock_localdate,
    ):
        mock_localdate.return_value = date(2026, 8, 31)

        august_number = generate_registration_number("4")

        mock_localdate.return_value = date(2026, 9, 1)

        september_number = generate_registration_number("4")

        self.assertEqual(
            august_number,
            "EA-04-202608-00001",
        )
        self.assertEqual(
            september_number,
            "EA-04-202609-00001",
        )


class MarkOrderAsPaidTests(TestCase):

    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=2000,
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="Česká republika",
        )

        self.participant_1 = OrderParticipant.objects.create(
            order=self.order,
            first_name="Jan",
            last_name="Novák",
            email="jan.novak@example.com",
        )

        self.participant_2 = OrderParticipant.objects.create(
            order=self.order,
            first_name="Petr",
            last_name="Svoboda",
            email="petr.svoboda@example.com",
        )

    @patch("courses.services.timezone.localdate")
    def test_mark_order_as_paid_changes_status_and_assigns_numbers(
        self,
        mock_localdate,
    ):
        mock_localdate.return_value = date(2026, 8, 7)

        order, participants, status_changed = mark_order_as_paid(
            self.order.id
        )

        order.refresh_from_db()
        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        self.assertEqual(order.status, "paid")
        self.assertIsNotNone(order.paid_at)
        self.assertTrue(status_changed)

        self.assertEqual(
            self.participant_1.registration_number,
            "EA-04-202608-00001",
        )
        self.assertEqual(
            self.participant_2.registration_number,
            "EA-04-202608-00002",
        )

        self.assertEqual(len(participants), 2)

    @patch("courses.services.timezone.localdate")
    def test_mark_order_as_paid_is_idempotent(
        self,
        mock_localdate,
    ):
        mock_localdate.return_value = date(2026, 8, 7)

        mark_order_as_paid(self.order.id)

        self.order.refresh_from_db()
        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        original_paid_at = self.order.paid_at
        original_number_1 = self.participant_1.registration_number
        original_number_2 = self.participant_2.registration_number

        order, participants, status_changed = mark_order_as_paid(
            self.order.id
        )

        order.refresh_from_db()
        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        self.assertFalse(status_changed)

        self.assertEqual(
            order.paid_at,
            original_paid_at,
        )
        self.assertEqual(
            self.participant_1.registration_number,
            original_number_1,
        )
        self.assertEqual(
            self.participant_2.registration_number,
            original_number_2,
        )

        sequence = RegistrationNumberSequence.objects.get(
            course_type="4",
            year=2026,
            month=8,
        )

        self.assertEqual(sequence.last_number, 2)

    @patch("courses.services.timezone.localdate")
    def test_existing_registration_number_is_not_replaced(
        self,
        mock_localdate,
    ):
        mock_localdate.return_value = date(2026, 8, 7)

        self.participant_1.registration_number = (
            "EA-04-202607-00123"
        )
        self.participant_1.save(
            update_fields=["registration_number"]
        )

        mark_order_as_paid(self.order.id)

        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        self.assertEqual(
            self.participant_1.registration_number,
            "EA-04-202607-00123",
        )

        self.assertEqual(
            self.participant_2.registration_number,
            "EA-04-202608-00001",
        )