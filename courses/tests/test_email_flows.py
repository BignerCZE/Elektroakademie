from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import (
    EmailLog,
    Order,
    OrderParticipant,
)


@override_settings(
    EMAIL_TRANSPORT="preview",
    SITE_URL="http://testserver",
)
class ActivationEmailFlowTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            course_type="4",
            total_price=1980,
            status="pending_payment",
            company_name="Testovací firma s.r.o.",
            street="Testovací 1",
            city="Praha",
            zip_code="11000",
            country="CZ",
            contact_first_name="Petr",
            contact_last_name="Svoboda",
            contact_email="kontakt@example.com",
        )

        self.participant_1 = (
            OrderParticipant.objects.create(
                order=self.order,
                first_name="Jan",
                last_name="Novák",
                email="jan@example.com",
            )
        )

        self.participant_2 = (
            OrderParticipant.objects.create(
                order=self.order,
                first_name="Eva",
                last_name="Nováková",
                email="eva@example.com",
            )
        )

        self.success_url = reverse(
            "order_payment_success",
            kwargs={
                "order_id": self.order.id,
            },
        )

    def test_payment_success_creates_activation_email_log_for_each_participant(
        self,
    ):
        response = self.client.get(
            self.success_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            "paid",
        )

        logs = EmailLog.objects.filter(
            email_type=(
                EmailLog.TYPE_PARTICIPANT_ACTIVATION
            ),
            order=self.order,
        ).order_by("recipient")

        self.assertEqual(
            logs.count(),
            2,
        )

        self.assertEqual(
            list(
                logs.values_list(
                    "recipient",
                    flat=True,
                )
            ),
            [
                "eva@example.com",
                "jan@example.com",
            ],
        )

        self.assertTrue(
            all(
                log.status
                == EmailLog.STATUS_PREVIEW
                for log in logs
            )
        )

    def test_payment_success_assigns_registration_numbers(
        self,
    ):
        self.client.get(
            self.success_url
        )

        self.participant_1.refresh_from_db()
        self.participant_2.refresh_from_db()

        self.assertIsNotNone(
            self.participant_1.registration_number
        )

        self.assertIsNotNone(
            self.participant_2.registration_number
        )

    def test_reloading_payment_success_does_not_create_duplicate_email_logs(
        self,
    ):
        self.client.get(
            self.success_url
        )

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=(
                    EmailLog.TYPE_PARTICIPANT_ACTIVATION
                ),
                order=self.order,
            ).count(),
            2,
        )

        self.client.get(
            self.success_url
        )

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=(
                    EmailLog.TYPE_PARTICIPANT_ACTIVATION
                ),
                order=self.order,
            ).count(),
            2,
        )

    def test_reloading_payment_success_does_not_change_paid_at(
        self,
    ):
        self.client.get(
            self.success_url
        )

        self.order.refresh_from_db()

        original_paid_at = self.order.paid_at

        self.client.get(
            self.success_url
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.paid_at,
            original_paid_at,
        )

    def test_activation_logs_have_correct_subject(
        self,
    ):
        self.client.get(
            self.success_url
        )

        logs = EmailLog.objects.filter(
            email_type=(
                EmailLog.TYPE_PARTICIPANT_ACTIVATION
            ),
            order=self.order,
        )

        for log in logs:
            self.assertEqual(
                log.subject,
                "Aktivace přístupu do Elektroakademie",
            )

    def test_activation_logs_are_not_marked_as_sent_in_preview_mode(
        self,
    ):
        self.client.get(
            self.success_url
        )

        logs = EmailLog.objects.filter(
            email_type=(
                EmailLog.TYPE_PARTICIPANT_ACTIVATION
            ),
            order=self.order,
        )

        for log in logs:
            self.assertEqual(
                log.status,
                EmailLog.STATUS_PREVIEW,
            )

            self.assertIsNone(
                log.sent_at,
            )

    def test_payment_success_creates_contact_email_log(
        self,
    ):
        self.client.get(
            self.success_url
        )

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            order=self.order,
        )

        self.assertEqual(
            log.recipient,
            "kontakt@example.com",
        )

        self.assertEqual(
            log.status,
            EmailLog.STATUS_PREVIEW,
        )

        self.assertIsNone(
            log.sent_at,
        )


    def test_payment_success_creates_exactly_three_email_logs(
        self,
    ):
        self.client.get(
            self.success_url
        )

        logs = EmailLog.objects.filter(
            order=self.order,
        )

        self.assertEqual(
            logs.count(),
            3,
        )

        self.assertEqual(
            logs.filter(
                email_type=(
                    EmailLog.TYPE_PARTICIPANT_ACTIVATION
                ),
            ).count(),
            2,
        )

        self.assertEqual(
            logs.filter(
                email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            ).count(),
            1,
        )


    def test_reloading_payment_success_does_not_duplicate_contact_email(
        self,
    ):
        self.client.get(
            self.success_url
        )

        self.client.get(
            self.success_url
        )

        self.assertEqual(
            EmailLog.objects.filter(
                email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
                order=self.order,
            ).count(),
            1,
        )


    def test_contact_email_has_expected_subject(
        self,
    ):
        self.client.get(
            self.success_url
        )

        log = EmailLog.objects.get(
            email_type=EmailLog.TYPE_PAYMENT_COMPLETED,
            order=self.order,
        )

        self.assertEqual(
            log.subject,
            (
                "Platba přijata – "
                "účastníci mohou zahájit studium"
            ),
        )