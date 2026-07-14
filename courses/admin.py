from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Certificate,
    Choice,
    Course,
    CustomUser,
    OrderParticipant,
    Payment,
    Question,
    QuestionCategory,
    QuizAttempt,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "questions_per_quiz", "order")
    list_filter = ("course",)
    search_fields = ("name", "course__title")
    ordering = ("course", "order", "name")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "course", "category")
    list_filter = ("course", "category")
    search_fields = ("text",)
    autocomplete_fields = ("category",)
    inlines = [ChoiceInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_paid",
        "passed_quiz",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    list_filter = (
        "is_active",
        "is_paid",
        "passed_quiz",
        "is_staff",
        "is_superuser",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Přístup do Elektroakademie",
            {
                "fields": (
                    "is_paid",
                    "passed_quiz",
                ),
                "description": (
                    "Zaškrtnutím pole Zaplaceno získá uživatel "
                    "přístup ke studiu a testům."
                ),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Osobní údaje",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                ),
            },
        ),
        (
            "Přístup do Elektroakademie",
            {
                "fields": (
                    "is_paid",
                    "passed_quiz",
                ),
            },
        ),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "amount", "is_successful", "created_at")
    list_filter = ("is_successful", "course", "created_at")
    search_fields = ("user__username", "course__title")

@admin.register(OrderParticipant)
class OrderParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "first_name",
        "last_name",
        "email",
        "order",
        "activation_completed_at",
    )

    search_fields = (
        "registration_number",
        "first_name",
        "last_name",
        "email",
    )

    list_filter = (
        "order__course_type",
        "activation_completed_at",
    )


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "attempt_number",
        "status",
        "score_percent",
        "passed",
        "submitted_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "course__title",
    )

    list_filter = (
        "status",
        "passed",
        "course",
    )

    readonly_fields = (
        "started_at",
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number",
        "participant",
        "quiz_attempt",
        "issued_at",
        "valid_until",
        "has_pdf",
    )

    list_filter = (
        "issued_at",
        "valid_until",
    )

    search_fields = (
        "certificate_number",
        "participant__registration_number",
        "participant__first_name",
        "participant__last_name",
        "participant__email",
    )

    readonly_fields = (
        "verification_token",
        "created_at",
    )

    autocomplete_fields = (
        "participant",
        "quiz_attempt",
    )

    ordering = (
        "-issued_at",
    )

    @admin.display(boolean=True, description="PDF")
    def has_pdf(self, obj):
        return bool(obj.pdf_file)