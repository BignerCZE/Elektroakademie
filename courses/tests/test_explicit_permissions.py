from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, RequestFactory
from django.urls import reverse

from courses.models import (
    Certificate, CustomUser, Course, EmailLog, Order, OrderParticipant, QuizAttempt,
)
from django.utils import timezone


class ExplicitPermissionTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(username="staff", is_staff=True)
        self.owner = CustomUser.objects.create_user(username="owner", is_paid=True)
        self.superuser = CustomUser.objects.create_superuser("super", "super@example.invalid", "Testheslo1")
        self.course = Course.objects.create(title="§4", description="x", video_url="https://example.invalid")
        self.order = Order.objects.create(course_type="4", company_name="Test", total_price=990, status="paid")
        self.participant = OrderParticipant.objects.create(
            order=self.order, user=self.owner, first_name="Jan", last_name="Test",
            email="jan@example.invalid", registration_number="EA-04-202611-00001",
        )
        self.attempt = QuizAttempt.objects.create(
            user=self.owner, course=self.course, status="submitted", passed=True,
            submitted_at=timezone.now(), score_percent=100,
        )
        self.certificate = Certificate.objects.create(
            participant=self.participant, quiz_attempt=self.attempt,
            certificate_number=self.participant.registration_number,
            valid_until=timezone.localdate(),
        )
        self.client.force_login(self.staff)

    def grant(self, *codenames):
        self.staff.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="courses", codename__in=codenames,
        ))

    def urls(self):
        return [
            reverse("participant_activation_email_preview", args=[self.participant.activation_token]),
            reverse("payment_completed_email_preview", args=[self.order.pk]),
            reverse("course_completed_email_preview", args=[self.attempt.pk]),
            reverse("course_completed_email_attachment", args=[self.attempt.pk, 0]),
            reverse("admin:courses_certificate_pdf", args=[self.certificate.pk]),
            reverse("admin:courses_emaillog_changelist"),
        ]

    @patch("courses.admin.generate_certificate_pdf")
    @patch("courses.views.build_course_completed_email")
    def test_staff_alone_grants_no_sensitive_access(self, builder, renderer):
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        builder.assert_not_called()
        renderer.assert_not_called()
        req = RequestFactory().get("/"); req.user = self.staff
        for model, model_admin in admin.site._registry.items():
            if model._meta.app_label != "courses":
                continue
            with self.subTest(model=model.__name__):
                self.assertFalse(model_admin.has_view_permission(req))
                self.assertFalse(model_admin.has_add_permission(req))
                self.assertFalse(model_admin.has_change_permission(req))
                self.assertFalse(model_admin.has_delete_permission(req))

    def test_explicit_preview_permissions_are_required_together(self):
        url = self.urls()[0]
        self.grant("view_orderparticipant")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.grant("view_order")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(self.urls()[2]).status_code, 403)

    @patch("courses.admin.generate_certificate_pdf", return_value=b"%PDF-test")
    def test_explicit_certificate_permission_allows_pdf_only(self, renderer):
        self.grant("view_certificate")
        self.assertEqual(self.client.get(self.urls()[4]).status_code, 200)
        renderer.assert_called_once()
        self.assertEqual(self.client.get(self.urls()[5]).status_code, 403)

    def test_explicit_log_permission_allows_read_only(self):
        self.grant("view_emaillog")
        self.assertEqual(self.client.get(self.urls()[5]).status_code, 200)
        req = RequestFactory().get("/"); req.user = self.staff
        self.assertFalse(admin.site._registry[EmailLog].has_change_permission(req))

    def test_delete_quiz_requires_delete_permission(self):
        req = RequestFactory().get("/"); req.user = self.staff
        ma = admin.site._registry[QuizAttempt]
        self.assertFalse(ma.has_delete_permission(req, self.attempt))
        self.grant("delete_quizattempt")
        self.staff = CustomUser.objects.get(pk=self.staff.pk)
        req.user = self.staff
        self.assertTrue(ma.has_delete_permission(req, self.attempt))

    def test_only_superuser_can_manage_accounts_roles_and_passwords(self):
        # Even explicitly delegated auth change permissions cannot be used
        # to grant access, replace a superuser password or edit group grants.
        self.staff.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_customuser", "change_customuser", "delete_customuser",
                          "add_group", "change_group", "delete_group"],
        ))
        group = Group.objects.create(name="test")
        for url in [
            reverse("admin:courses_customuser_add"),
            reverse("admin:courses_customuser_change", args=[self.staff.pk]),
            reverse("admin:auth_user_password_change", args=[self.superuser.pk]),
            reverse("admin:auth_group_change", args=[group.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {"is_superuser": "on"}).status_code, 403)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_superuser)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("admin:courses_customuser_change", args=[self.staff.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:auth_group_change", args=[group.pk])).status_code, 200)

    def test_superuser_keeps_sensitive_access(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(self.urls()[0]).status_code, 200)
        self.assertEqual(self.client.get(self.urls()[5]).status_code, 200)
