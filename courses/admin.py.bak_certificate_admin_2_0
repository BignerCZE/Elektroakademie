import csv
import uuid

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils import timezone

from .models import (
    Certificate,
    Choice,
    Course,
    CustomUser,
    EmailLog,
    Order,
    OrderParticipant,
    Payment,
    ParticipantProfile,
    Question,
    QuestionCategory,
    QuizAttempt,
    QuizAttemptQuestion,
)

from .services import mark_order_as_paid


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "course",
        "questions_per_quiz",
        "order",
    )
    list_filter = ("course",)
    search_fields = (
        "name",
        "course__title",
    )
    ordering = (
        "course",
        "order",
        "name",
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "course",
        "category",
    )

    list_filter = (
        "course",
        "category",
    )

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
    list_display = (
        "user",
        "course",
        "amount",
        "is_successful",
        "created_at",
    )
    list_filter = (
        "is_successful",
        "course",
        "created_at",
    )
    search_fields = (
        "user__username",
        "course__title",
    )



class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"
        labels = {
            "course_type": "Typ kurzu",
            "status": "Stav",
            "total_price": "Cena",
        }


class OrderParticipantInline(admin.TabularInline):
    model = OrderParticipant
    extra = 0
    show_change_link = False
    can_delete = False

    fields = (
        "registration_number",
        "participant_name",
        "email",
        "participant_status",
        "quiz_status",
        "certificate_status",
        "participant_detail_link",
    )

    readonly_fields = fields

    ordering = (
        "last_name",
        "first_name",
    )

    verbose_name = "Účastník"
    verbose_name_plural = "Účastníci objednávky"

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .select_related(
                "order",
                "user",
            )
        )

        profile_queryset = ParticipantProfile.objects.filter(
            participant_id=OuterRef("pk")
        )

        certificate_queryset = Certificate.objects.filter(
            participant_id=OuterRef("pk")
        )

        submitted_attempts = QuizAttempt.objects.filter(
            user_id=OuterRef("user_id"),
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        passed_attempts = submitted_attempts.filter(
            passed=True,
        )

        in_progress_attempts = QuizAttempt.objects.filter(
            user_id=OuterRef("user_id"),
            status=QuizAttempt.STATUS_IN_PROGRESS,
        )

        latest_submitted_attempt = submitted_attempts.order_by(
            "-submitted_at",
            "-started_at",
        )

        return queryset.annotate(
            admin_has_profile=Exists(
                profile_queryset
            ),
            admin_has_certificate=Exists(
                certificate_queryset
            ),
            admin_has_submitted_quiz=Exists(
                submitted_attempts
            ),
            admin_has_passed_quiz=Exists(
                passed_attempts
            ),
            admin_has_in_progress_quiz=Exists(
                in_progress_attempts
            ),
            admin_latest_score=Subquery(
                latest_submitted_attempt.values(
                    "score_percent"
                )[:1]
            ),
        )

    @admin.display(description="Účastník")
    def participant_name(self, obj):
        if not obj or not obj.pk:
            return "—"

        return f"{obj.first_name} {obj.last_name}".strip()

    @admin.display(description="Stav")
    def participant_status(self, obj):
        if not obj or not obj.pk:
            return "—"

        if obj.order.status != "paid":
            return self._status_badge(
                "Čeká na platbu",
                "#6b7280",
            )

        if not obj.activation_completed_at:
            return self._status_badge(
                "Čeká na aktivaci",
                "#c58a00",
            )

        if not obj.user_id:
            return self._status_badge(
                "Chybí účet",
                "#ba2121",
            )

        if not obj.admin_has_profile:
            return self._status_badge(
                "Čeká na profil",
                "#c58a00",
            )

        if obj.admin_has_certificate:
            return self._status_badge(
                "Certifikát vystaven",
                "#417690",
            )

        if obj.admin_has_passed_quiz:
            return self._status_badge(
                "Test splněn",
                "#2e7d32",
            )

        if obj.admin_has_submitted_quiz:
            return self._status_badge(
                "Test nesplněn",
                "#ba2121",
            )

        if obj.admin_has_in_progress_quiz:
            return self._status_badge(
                "Test rozpracován",
                "#417690",
            )

        return self._status_badge(
            "Studuje",
            "#417690",
        )

    @staticmethod
    def _status_badge(label, color):
        return format_html(
            (
                '<span style="'
                'display:inline-block;'
                'padding:4px 9px;'
                'border-radius:12px;'
                'background:{};'
                'color:#fff;'
                'font-weight:600;'
                'font-size:12px;'
                'line-height:1.2;'
                'white-space:nowrap;'
                '">{}</span>'
            ),
            color,
            label,
        )

    @admin.display(description="Test")
    def quiz_status(self, obj):
        if not obj or not obj.pk or not obj.user_id:
            return "—"

        if obj.admin_has_passed_quiz:
            if obj.admin_latest_score is not None:
                return format_html(
                    '<span style="color:#7bbf64;font-weight:600;">{}</span>',
                    f"Splněn ({obj.admin_latest_score} %)",
                )

            return format_html(
                '<span style="color:#7bbf64;font-weight:600;">{}</span>',
                "Splněn",
            )

        if obj.admin_has_submitted_quiz:
            if obj.admin_latest_score is not None:
                return format_html(
                    '<span style="color:#e35d6a;font-weight:600;">{}</span>',
                    f"Nesplněn ({obj.admin_latest_score} %)",
                )

            return format_html(
                '<span style="color:#e35d6a;font-weight:600;">{}</span>',
                "Nesplněn",
            )

        if obj.admin_has_in_progress_quiz:
            return "Rozpracovaný"

        return "Nezahájen"

    @admin.display(description="Certifikát")
    def certificate_status(self, obj):
        if not obj or not obj.pk:
            return "—"

        if obj.admin_has_certificate:
            return format_html(
                '<span style="color:#7bbf64;font-weight:700;">{}</span>',
                "✓ Ano",
            )

        return format_html(
            '<span style="color:#e35d6a;">{}</span>',
            "✕ Ne",
        )

    @admin.display(description="")
    def participant_detail_link(self, obj):
        if not obj or not obj.pk:
            return "—"

        url = reverse(
            "admin:courses_orderparticipant_change",
            args=[obj.pk],
        )

        return format_html(
            (
                '<a href="{}" '
                'style="'
                'display:inline-block;'
                'padding:5px 10px;'
                'border-radius:4px;'
                'background:#417690;'
                'color:#fff;'
                'font-weight:600;'
                'text-decoration:none;'
                'white-space:nowrap;'
                '">'
                "Detail →"
                "</a>"
            ),
            url,
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": (
                "courses/admin/order_detail.css",
            )
        }
    form = OrderAdminForm
    list_display = (
        "id",
        "created_at",
        "course_type_display",
        "company_name",
        "contact_person",
        "participant_count",
        "activation_progress",
        "total_price_display",
        "status_display",
        "paid_at",
    )

    list_display_links = (
        "id",
        "company_name",
    )

    list_filter = (
        "status",
        "course_type",
        "created_at",
        "paid_at",
    )

    search_fields = (
        "=id",
        "company_name",
        "ico",
        "dic",
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "contact_phone",
        "participants__registration_number",
        "participants__first_name",
        "participants__last_name",
        "participants__email",
    )

    readonly_fields = (
        "status",
        "order_dashboard",
        "created_at",
        "paid_at",
        "participants_overview",
        "participant_summary",
        "total_price_detail",
    )

    fieldsets = (
        (
            "Pracovní souhrn",
            {
                "fields": (
                    "order_dashboard",
                ),
                "classes": (
                    "order-dashboard-fieldset",
                ),
            },
        ),
        (
            "Účastníci objednávky",
            {
                "fields": (
                    "participants_overview",
                ),
                "classes": (
                    "participants-overview-fieldset",
                ),
            },
        ),
        (
            "Kontaktní osoba",
            {
                "fields": (
                    (
                        "contact_first_name",
                        "contact_last_name",
                    ),
                    (
                        "contact_phone_prefix",
                        "contact_phone",
                    ),
                    "contact_email",
                ),
            },
        ),
        (
            "Fakturační údaje",
            {
                "fields": (
                    "ico",
                    "dic",
                    "company_name",
                    "street",
                    (
                        "zip_code",
                        "city",
                    ),
                    "country",
                ),
            },
        ),
        (
            "Doplňující informace",
            {
                "fields": ("note",),
            },
        ),
    )


    actions = [
        "mark_selected_orders_as_paid",
    ]

    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    save_on_top = True

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.annotate(
            admin_participant_count=Count(
                "participants",
                distinct=True,
            ),
            admin_activated_count=Count(
                "participants",
                filter=Q(
                    participants__activation_completed_at__isnull=False,
                ),
                distinct=True,
            ),
        )

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(
            super().get_fieldsets(request, obj)
        )

        if obj and obj.status == "paid":
            order_fields = (
                "course_type",
                "total_price_detail",
            )
        else:
            order_fields = (
                "course_type",
                "total_price",
            )

        order_fieldset = (
            "Údaje objednávky",
            {
                "fields": (
                    order_fields,
                ),
                "classes": (
                    "order-summary-fieldset",
                ),
            },
        )

        fieldsets.insert(
            1,
            order_fieldset,
        )

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(
            super().get_readonly_fields(request, obj)
        )

        if obj and obj.status == "paid":
            readonly_fields.extend(
                [
                    "course_type",
                    "total_price",
                ]
            )

        return readonly_fields

    @admin.display(
        description="Kurz",
        ordering="course_type",
    )
    def course_type_display(self, obj):
        return obj.get_course_type_display()

    @admin.display(
        description="Kontaktní osoba",
        ordering="contact_last_name",
    )
    def contact_person(self, obj):
        return obj.contact_full_name or "—"

    @admin.display(
        description="Účastníci",
        ordering="admin_participant_count",
    )
    def participant_count(self, obj):
        return obj.admin_participant_count

    @admin.display(
        description="Aktivace",
        ordering="admin_activated_count",
    )
    def activation_progress(self, obj):
        return (
            f"{obj.admin_activated_count}/"
            f"{obj.admin_participant_count}"
        )

    @admin.display(
        description="Cena",
        ordering="total_price",
    )
    def total_price_display(self, obj):
        return f"{obj.total_price:,} Kč".replace(",", " ")

    @admin.display(
        description="Stav",
        ordering="status",
    )
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.display(description="Cena")
    def total_price_detail(self, obj):
        if not obj or obj.total_price is None:
            return "—"

        return f"{obj.total_price:,} Kč".replace(",", " ")

    @admin.display(description="")
    def order_dashboard(self, obj):
        if not obj or not obj.pk:
            return "Souhrn bude dostupný po vytvoření objednávky."

        participants = obj.participants.all()

        total_participants = participants.count()

        activated_count = participants.filter(
            activation_completed_at__isnull=False
        ).count()

        waiting_activation_count = (
            total_participants - activated_count
        )

        certificate_count = Certificate.objects.filter(
            participant__order=obj
        ).count()

        if obj.status == "paid":
            status_text = "Zaplaceno"
            status_color = "#2e7d32"
        else:
            status_text = "Čeká na platbu"
            status_color = "#c58a00"

        course_name = obj.get_course_type_display()

        created_at = (
            obj.created_at.strftime("%d.%m.%Y %H:%M")
            if obj.created_at
            else "—"
        )

        paid_at = (
            obj.paid_at.strftime("%d.%m.%Y %H:%M")
            if obj.paid_at
            else "—"
        )

        return format_html(
            """
            <div style="
                display:grid;
                grid-template-columns:repeat(4, minmax(150px, 1fr));
                gap:12px;
                margin:2px 0 6px 0;
            ">

                <div style="
                    padding:14px 16px;
                    background:#202020;
                    border:1px solid #333;
                    border-radius:6px;
                ">
                    <div style="
                        color:#aaa;
                        font-size:11px;
                        text-transform:uppercase;
                        margin-bottom:5px;
                    ">
                        Kurz
                    </div>
                    <div style="
                        font-size:15px;
                        font-weight:600;
                    ">
                        {}
                    </div>
                </div>

                <div style="
                    padding:14px 16px;
                    background:#202020;
                    border:1px solid #333;
                    border-radius:6px;
                ">
                    <div style="
                        color:#aaa;
                        font-size:11px;
                        text-transform:uppercase;
                        margin-bottom:5px;
                    ">
                        Stav objednávky
                    </div>
                    <span style="
                        display:inline-block;
                        padding:4px 9px;
                        border-radius:12px;
                        background:{};
                        color:#fff;
                        font-size:12px;
                        font-weight:600;
                    ">
                        {}
                    </span>
                </div>

                <div style="
                    padding:14px 16px;
                    background:#202020;
                    border:1px solid #333;
                    border-radius:6px;
                ">
                    <div style="
                        color:#aaa;
                        font-size:11px;
                        text-transform:uppercase;
                        margin-bottom:5px;
                    ">
                        Účastníci
                    </div>
                    <div style="
                        font-size:18px;
                        font-weight:600;
                    ">
                        {}
                    </div>
                    <div style="
                        color:#aaa;
                        font-size:12px;
                        margin-top:3px;
                    ">
                        Aktivováno {} / {}
                    </div>
                </div>

                <div style="
                    padding:14px 16px;
                    background:#202020;
                    border:1px solid #333;
                    border-radius:6px;
                ">
                    <div style="
                        color:#aaa;
                        font-size:11px;
                        text-transform:uppercase;
                        margin-bottom:5px;
                    ">
                        Certifikáty
                    </div>
                    <div style="
                        font-size:18px;
                        font-weight:600;
                    ">
                        {} / {}
                    </div>
                </div>

            </div>

            <div style="
                display:flex;
                flex-wrap:wrap;
                gap:18px;
                padding:10px 2px 0 2px;
                color:#aaa;
                font-size:12px;
            ">
                <span>
                    Vytvořeno:
                    <strong style="color:#ddd;">{}</strong>
                </span>

                <span>
                    Zaplaceno:
                    <strong style="color:#ddd;">{}</strong>
                </span>

                <span>
                    Čeká na aktivaci:
                    <strong style="color:#ddd;">{}</strong>
                </span>
            </div>
            """,
            course_name,
            status_color,
            status_text,
            total_participants,
            activated_count,
            total_participants,
            certificate_count,
            total_participants,
            created_at,
            paid_at,
            waiting_activation_count,
        )

    @admin.display(description="")
    def participants_overview(self, obj):
        if not obj or not obj.pk:
            return "Účastníci budou dostupní po vytvoření objednávky."

        participants = (
            obj.participants
            .select_related(
                "user",
            )
            .annotate(
                admin_has_profile=Exists(
                    ParticipantProfile.objects.filter(
                        participant_id=OuterRef("pk")
                    )
                ),
                admin_has_certificate=Exists(
                    Certificate.objects.filter(
                        participant_id=OuterRef("pk")
                    )
                ),
                admin_has_submitted_quiz=Exists(
                    QuizAttempt.objects.filter(
                        user_id=OuterRef("user_id"),
                        status=QuizAttempt.STATUS_SUBMITTED,
                    )
                ),
                admin_has_passed_quiz=Exists(
                    QuizAttempt.objects.filter(
                        user_id=OuterRef("user_id"),
                        status=QuizAttempt.STATUS_SUBMITTED,
                        passed=True,
                    )
                ),
                admin_has_in_progress_quiz=Exists(
                    QuizAttempt.objects.filter(
                        user_id=OuterRef("user_id"),
                        status=QuizAttempt.STATUS_IN_PROGRESS,
                    )
                ),
                admin_latest_score=Subquery(
                    QuizAttempt.objects.filter(
                        user_id=OuterRef("user_id"),
                        status=QuizAttempt.STATUS_SUBMITTED,
                    )
                    .order_by(
                        "-submitted_at",
                        "-started_at",
                    )
                    .values("score_percent")[:1]
                ),
            )
            .order_by(
                "last_name",
                "first_name",
            )
        )

        rows = []

        for participant in participants:
            if obj.status != "paid":
                status = self._participant_badge(
                    "Čeká na platbu",
                    "#6b7280",
                )
            elif not participant.activation_completed_at:
                status = self._participant_badge(
                    "Čeká na aktivaci",
                    "#c58a00",
                )
            elif not participant.user_id:
                status = self._participant_badge(
                    "Chybí účet",
                    "#ba2121",
                )
            elif not participant.admin_has_profile:
                status = self._participant_badge(
                    "Čeká na profil",
                    "#c58a00",
                )
            elif participant.admin_has_certificate:
                status = self._participant_badge(
                    "Certifikát vystaven",
                    "#2e7d32",
                )
            elif participant.admin_has_passed_quiz:
                status = self._participant_badge(
                    "Test splněn",
                    "#2e7d32",
                )
            elif participant.admin_has_submitted_quiz:
                status = self._participant_badge(
                    "Test nesplněn",
                    "#ba2121",
                )
            elif participant.admin_has_in_progress_quiz:
                status = self._participant_badge(
                    "Test rozpracován",
                    "#417690",
                )
            else:
                status = self._participant_badge(
                    "Studuje",
                    "#417690",
                )

            if not participant.user_id:
                quiz = self._participant_badge(
                    "Nedostupný",
                    "#6b7280",
                )

            elif participant.admin_has_passed_quiz:
                if participant.admin_latest_score is not None:
                    quiz = self._participant_badge(
                        f"Splněn ({participant.admin_latest_score} %)",
                        "#2e7d32",
                    )
                else:
                    quiz = self._participant_badge(
                        "Splněn",
                        "#2e7d32",
                    )

            elif participant.admin_has_submitted_quiz:
                if participant.admin_latest_score is not None:
                    quiz = self._participant_badge(
                        f"Nesplněn ({participant.admin_latest_score} %)",
                        "#ba2121",
                    )
                else:
                    quiz = self._participant_badge(
                        "Nesplněn",
                        "#ba2121",
                    )

            elif participant.admin_has_in_progress_quiz:
                quiz = self._participant_badge(
                    "Rozpracován",
                    "#417690",
                )

            else:
                quiz = self._participant_badge(
                    "Nezahájen",
                    "#6b7280",
                )

            if participant.admin_has_certificate:
                certificate = format_html(
                    '<span style="color:#7bbf64;font-weight:600;">{}</span>',
                    "✓ Ano",
                )
            else:
                certificate = format_html(
                    '<span style="color:#e35d6a;">{}</span>',
                    "✕ Ne",
                )

            detail_url = reverse(
                "admin:courses_orderparticipant_change",
                args=[participant.pk],
            )

            rows.append(
                format_html(
                    """
                    <tr>
                        <td style="
                            white-space:nowrap;
                            font-weight:700;
                            font-family:Consolas, 'Courier New', monospace;
                            letter-spacing:0.4px;
                            color:#f3f3f3;
                        ">
                            {}
                        </td>                        
                        <td>
                            <a href="{}"
                            style="
                                    color:#ffffff;
                                    font-weight:700;
                                    text-decoration:none;
                            ">
                                {}
                            </a>
                        </td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td style="text-align:right;">
                            <a href="{}"
                            style="
                                display:inline-block;
                                padding:6px 11px;
                                border-radius:4px;
                                background:#417690;
                                color:#fff;
                                font-weight:600;
                                text-decoration:none;
                                white-space:nowrap;
                            ">
                                Detail →
                            </a>
                        </td>
                    </tr>
                    """,
                    participant.registration_number or "—",
                    detail_url,
                    f"{participant.first_name} {participant.last_name}".strip(),
                    participant.email,
                    status,
                    quiz,
                    certificate,
                    detail_url,
                )
            )

        if not rows:
            body = format_html(
                '<tr><td colspan="7" style="padding:16px;">{}</td></tr>',
                "Objednávka nemá žádné účastníky.",
            )
        else:
            body = format_html_join(
                "",
                "{}",
                ((row,) for row in rows),
            )

        return format_html(
            """
            <div style="width:100%;overflow-x:auto;">
                <table style="
                    width:100%;
                    border-collapse:collapse;
                    margin:0;
                ">
                    <thead>
                        <tr style="color:#bbb;font-size:11px;text-transform:uppercase;">
                            <th style="text-align:left;padding:8px 10px;">Evidenční číslo</th>
                            <th style="text-align:left;padding:8px 10px;">Účastník</th>
                            <th style="text-align:left;padding:8px 10px;">E-mail</th>
                            <th style="text-align:left;padding:8px 10px;">Stav</th>
                            <th style="text-align:left;padding:8px 10px;">Test</th>
                            <th style="text-align:left;padding:8px 10px;">Certifikát</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>{}</tbody>
                </table>
            </div>
            """,
            body,
        )

    @admin.display(description="Souhrn účastníků")
    def participant_summary(self, obj):
        if not obj or not obj.pk:
            return "Objednávku je nejprve nutné uložit."

        total = getattr(
            obj,
            "admin_participant_count",
            obj.participants.count(),
        )

        activated = getattr(
            obj,
            "admin_activated_count",
            obj.participants.filter(
                activation_completed_at__isnull=False,
            ).count(),
        )

        with_account = obj.participants.filter(
            user__isnull=False,
        ).count()

        return (
            f"Celkem: {total} | "
            f"Aktivováno: {activated} | "
            f"Uživatelský účet: {with_account}"
        )

    @admin.action(
        description="Označit vybrané objednávky jako zaplacené"
    )
    def mark_selected_orders_as_paid(self, request, queryset):
        newly_paid_count = 0
        already_paid_count = 0
        error_count = 0

        for order in queryset.order_by("id"):
            try:
                _, _, status_changed = mark_order_as_paid(
                    order.pk
                )
            except Order.DoesNotExist:
                error_count += 1
                continue
            except Exception:
                error_count += 1
                continue

            if status_changed:
                newly_paid_count += 1
            else:
                already_paid_count += 1

        if newly_paid_count:
            self.message_user(
                request,
                (
                    "Počet nově zaplacených objednávek: "
                    f"{newly_paid_count}."
                ),
                level=messages.SUCCESS,
            )

        if already_paid_count:
            self.message_user(
                request,
                (
                    "Počet objednávek, které již byly "
                    f"zaplacené: {already_paid_count}."
                ),
                level=messages.INFO,
            )

        if error_count:
            self.message_user(
                request,
                (
                    "Počet objednávek, které se nepodařilo "
                    f"zpracovat: {error_count}."
                ),
                level=messages.ERROR,
            )
    @staticmethod
    def _participant_badge(label, color):
        return format_html(
            """
            <span style="
                display:inline-block;
                padding:4px 9px;
                border-radius:12px;
                background:{};
                color:#fff;
                font-weight:600;
                font-size:12px;
                white-space:nowrap;
            ">{}</span>
            """,
            color,
            label,
        )


class ActivationStatusFilter(admin.SimpleListFilter):
    title = "stav aktivace"
    parameter_name = "activation_status"

    def lookups(self, request, model_admin):
        return (
            ("activated", "Aktivováno"),
            ("not_activated", "Neaktivováno"),
        )

    def queryset(self, request, queryset):
        if self.value() == "activated":
            return queryset.filter(
                activation_completed_at__isnull=False
            )

        if self.value() == "not_activated":
            return queryset.filter(
                activation_completed_at__isnull=True
            )

        return queryset


class AccountStatusFilter(admin.SimpleListFilter):
    title = "uživatelský účet"
    parameter_name = "account_status"

    def lookups(self, request, model_admin):
        return (
            ("exists", "Účet existuje"),
            ("missing", "Účet chybí"),
            ("active", "Aktivní účet"),
            ("inactive", "Neaktivní účet"),
        )

    def queryset(self, request, queryset):
        if self.value() == "exists":
            return queryset.filter(user__isnull=False)

        if self.value() == "missing":
            return queryset.filter(user__isnull=True)

        if self.value() == "active":
            return queryset.filter(
                user__isnull=False,
                user__is_active=True,
            )

        if self.value() == "inactive":
            return queryset.filter(
                user__isnull=False,
                user__is_active=False,
            )

        return queryset


class ProfileStatusFilter(admin.SimpleListFilter):
    title = "profil účastníka"
    parameter_name = "profile_status"

    def lookups(self, request, model_admin):
        return (
            ("exists", "Profil vyplněn"),
            ("missing", "Profil chybí"),
        )

    def queryset(self, request, queryset):
        if self.value() == "exists":
            return queryset.filter(profile__isnull=False)

        if self.value() == "missing":
            return queryset.filter(profile__isnull=True)

        return queryset


class QuizStatusFilter(admin.SimpleListFilter):
    title = "stav testu"
    parameter_name = "quiz_status"

    def lookups(self, request, model_admin):
        return (
            ("passed", "Test splněn"),
            ("failed", "Test nesplněn"),
            ("not_taken", "Bez odeslaného testu"),
            ("in_progress", "Rozpracovaný test"),
        )

    def queryset(self, request, queryset):
        if self.value() == "passed":
            return queryset.filter(
                user__quiz_attempts__status=(
                    QuizAttempt.STATUS_SUBMITTED
                ),
                user__quiz_attempts__passed=True,
            ).distinct()

        if self.value() == "failed":
            return queryset.filter(
                user__quiz_attempts__status=(
                    QuizAttempt.STATUS_SUBMITTED
                ),
                user__quiz_attempts__passed=False,
            ).exclude(
                user__quiz_attempts__passed=True
            ).distinct()

        if self.value() == "not_taken":
            return queryset.exclude(
                user__quiz_attempts__status=(
                    QuizAttempt.STATUS_SUBMITTED
                )
            ).distinct()

        if self.value() == "in_progress":
            return queryset.filter(
                user__quiz_attempts__status=(
                    QuizAttempt.STATUS_IN_PROGRESS
                )
            ).distinct()

        return queryset


class CertificateStatusFilter(admin.SimpleListFilter):
    title = "certifikát"
    parameter_name = "certificate_status"

    def lookups(self, request, model_admin):
        return (
            ("issued", "Certifikát vystaven"),
            ("missing", "Certifikát nevystaven"),
        )

    def queryset(self, request, queryset):
        if self.value() == "issued":
            return queryset.filter(certificate__isnull=False)

        if self.value() == "missing":
            return queryset.filter(certificate__isnull=True)

        return queryset


@admin.register(OrderParticipant)
class OrderParticipantAdmin(admin.ModelAdmin):

    class Media:
        css = {
            "all": ("courses/admin/participant_detail.css",)
        }

    list_display = (
        "registration_number_display",
        "participant_name",
        "email",
        "course_display",
        "company_display",
        "payment_status",
        "activation_status",
        "account_status",
        "profile_status",
        "quiz_status",
        "certificate_status",
    )

    list_display_links = (
        "registration_number_display",
        "participant_name",
    )

    list_filter = (
        "order__course_type",
        "order__status",
        ActivationStatusFilter,
        AccountStatusFilter,
        ProfileStatusFilter,
        QuizStatusFilter,
        CertificateStatusFilter,
    )

    search_fields = (
        "registration_number",
        "first_name",
        "last_name",
        "email",
        "=order__id",
        "order__company_name",
        "order__ico",
        "order__contact_first_name",
        "order__contact_last_name",
        "order__contact_email",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "activation_link",
        "activation_token",
        "activation_sent_at",
        "activation_completed_at",
        "account_link",
        "participant_dashboard",
        "order_summary",
        "account_summary",
        "activation_summary",
        "profile_summary",
        "quiz_summary",
        "certificate_summary",
        "email_history_summary",
    )

    fieldsets = (
        (
            "Pracovní souhrn",
            {
                "fields": (
                    "participant_dashboard",
                ),
            },
        ),
        (
            "Účastník",
            {
                "fields": (
                    "order_summary",
                    "registration_number",
                    (
                        "first_name",
                        "last_name",
                    ),
                    "email",
                ),
            },
        ),
        (
            "Aktivace a uživatelský účet",
            {
                "fields": (
                    "account_summary",
                    "activation_summary",
                ),
                "classes": (
                    "participant-account-fieldset",
                ),
            },
        ),
        (
            "Technické údaje aktivace",
            {
                "fields": (
                    "activation_token",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Výsledek kurzu",
            {
                "fields": (
                    "profile_summary",
                    "quiz_summary",
                    "certificate_summary",
                    "email_history_summary",
                ),
                "classes": (
                    "participant-related-fieldset",
                ),
            },
        ),
    )

    list_select_related = (
        "order",
        "user",
    )

    ordering = (
        "last_name",
        "first_name",
    )

    list_per_page = 50
    save_on_top = True

    actions = (
        "regenerate_activation_tokens",
        "export_participants_to_csv",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        profile_queryset = ParticipantProfile.objects.filter(
            participant_id=OuterRef("pk")
        )

        certificate_queryset = Certificate.objects.filter(
            participant_id=OuterRef("pk")
        )

        submitted_attempts = QuizAttempt.objects.filter(
            user_id=OuterRef("user_id"),
            status=QuizAttempt.STATUS_SUBMITTED,
        )

        passed_attempts = submitted_attempts.filter(
            passed=True
        )

        in_progress_attempts = QuizAttempt.objects.filter(
            user_id=OuterRef("user_id"),
            status=QuizAttempt.STATUS_IN_PROGRESS,
        )

        latest_submitted_attempt = submitted_attempts.order_by(
            "-submitted_at",
            "-started_at",
        )

        return queryset.annotate(
            admin_has_profile=Exists(profile_queryset),
            admin_has_certificate=Exists(
                certificate_queryset
            ),
            admin_has_submitted_quiz=Exists(
                submitted_attempts
            ),
            admin_has_passed_quiz=Exists(
                passed_attempts
            ),
            admin_has_in_progress_quiz=Exists(
                in_progress_attempts
            ),
            admin_latest_score=Subquery(
                latest_submitted_attempt.values(
                    "score_percent"
                )[:1]
            ),
        )

    @staticmethod
    def _format_admin_datetime(value):
        if not value:
            return "—"

        return timezone.localtime(
            value
        ).strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _render_detail_badge(label, css_class):
        return format_html(
            (
                '<span class="participant-dashboard__badge {}">'
                "{}"
                "</span>"
            ),
            css_class,
            label,
        )

    @staticmethod
    def _render_detail_items(items):
        if not items:
            return ""

        body = format_html_join(
            "",
            (
                "<div>"
                "<span>{}</span>"
                "<strong>{}</strong>"
                "</div>"
            ),
            items,
        )

        return format_html(
            (
                '<div class="participant-detail-card__grid">'
                "{}"
                "</div>"
            ),
            body,
        )

    @staticmethod
    def _render_detail_link(url, label):
        return format_html(
            (
                '<div class="participant-detail-card__actions">'
                '<a href="{}" class="participant-detail-card__button">'
                "{}"
                "</a>"
                "</div>"
            ),
            url,
            label,
        )

    def _render_detail_card(
        self,
        *,
        title,
        subtitle,
        badge_label,
        badge_class,
        items=(),
        body="",
        actions="",
    ):
        badge = self._render_detail_badge(
            badge_label,
            badge_class,
        )

        items_html = self._render_detail_items(items)

        return format_html(
            """
            <div class="participant-detail-card">

                <div class="participant-detail-card__header">

                    <div>
                        <div class="participant-detail-card__title">
                            {}
                        </div>

                        <div class="participant-detail-card__subtitle">
                            {}
                        </div>
                    </div>

                    {}

                </div>

                {}

                {}

                {}

            </div>
            """,
            title,
            subtitle,
            badge,
            items_html,
            body,
            actions,
        )

    @staticmethod
    def _render_dashboard_card(
        title,
        value,
        badge_text,
        badge_class,
        *,
        small_value=False,
    ):
        value_class = (
            "participant-dashboard__card-value "
            "participant-dashboard__card-value--small"
            if small_value
            else "participant-dashboard__card-value"
        )

        return format_html(
            """
            <div class="participant-dashboard__card">
                <div class="participant-dashboard__card-label">
                    {}
                </div>

                <div class="{}">
                    {}
                </div>

                <div class="participant-dashboard__badge {}">
                    {}
                </div>
            </div>
            """,
            title,
            value_class,
            value,
            badge_class,
            badge_text,
        )

    @admin.display(description="")
    def order_summary(self, obj):
        if not obj or not obj.pk or not obj.order_id:
            return "Objednávka není přiřazena."

        order = obj.order

        detail_url = reverse(
            "admin:courses_order_change",
            args=[order.pk],
        )

        if order.status == "paid":
            status_label = "Zaplaceno"
            status_class = "status-success"
        else:
            status_label = "Čeká na platbu"
            status_class = "status-warning"

        return self._render_detail_card(
            title="Objednávka",
            subtitle="Objednávka, ze které účastník vznikl.",
            badge_label=status_label,
            badge_class=status_class,
            items=(
                (
                    "Objednávka",
                    f"#{order.pk}",
                ),
                (
                    "Kurz",
                    order.get_course_type_display(),
                ),
                (
                    "Objednatel",
                    order.company_name or "—",
                ),
                (
                    "Vytvořeno",
                    self._format_admin_datetime(
                        order.created_at
                    ),
                ),
                (
                    "Zaplaceno",
                    self._format_admin_datetime(
                        order.paid_at
                    ),
                ),
            ),
            actions=self._render_detail_link(
                detail_url,
                "Otevřít objednávku →",
            ),
        )

    @admin.display(description="")
    def account_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        if not obj.user_id:
            return self._render_detail_card(
                title="Uživatelský účet",
                subtitle="Účet zatím nebyl vytvořen.",
                badge_label="Nevytvořen",
                badge_class="status-neutral",
            )

        user = obj.user

        detail_url = reverse(
            "admin:courses_customuser_change",
            args=[user.pk],
        )

        if user.is_active:
            status_label = "Aktivní"
            status_class = "status-success"
        else:
            status_label = "Neaktivní"
            status_class = "status-danger"

        return self._render_detail_card(
            title="Uživatelský účet",
            subtitle=(
                "Účet používaný účastníkem pro přístup "
                "do Elektroakademie."
            ),
            badge_label=status_label,
            badge_class=status_class,
            items=(
                (
                    "E-mail",
                    user.email or "—",
                ),
                (
                    "Uživatelské jméno",
                    user.username or "—",
                ),
                (
                    "Jméno účtu",
                    user.get_full_name().strip() or "—",
                ),
                (
                    "ID účtu",
                    user.pk,
                ),
            ),
            actions=self._render_detail_link(
                detail_url,
                "Otevřít účet →",
            ),
        )

    @admin.display(description="")
    def activation_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        order_paid = (
            obj.order_id
            and obj.order.status == "paid"
        )

        if obj.activation_completed_at:
            status_label = "Dokončeno"
            status_class = "status-success"
            status_value = "Aktivováno"

        elif not order_paid:
            status_label = "Čeká na platbu"
            status_class = "status-neutral"
            status_value = "Aktivace není dostupná"

        elif obj.activation_sent_at:
            status_label = "Čeká na aktivaci"
            status_class = "status-warning"
            status_value = "Odkaz odeslán"

        elif obj.activation_token:
            status_label = "Čeká na aktivaci"
            status_class = "status-warning"
            status_value = "Odkaz připraven"

        else:
            status_label = "Bez odkazu"
            status_class = "status-danger"
            status_value = "Aktivační odkaz chybí"

        activation_action = ""

        if (
            order_paid
            and not obj.activation_completed_at
            and obj.activation_token
            and not obj.user_id
        ):
            relative_url = reverse(
                "participant_activation",
                args=[obj.activation_token],
            )

            request = getattr(
                self,
                "_current_request",
                None,
            )

            activation_url = (
                request.build_absolute_uri(relative_url)
                if request
                else relative_url
            )

            activation_action = format_html(
                """
                <div class="participant-detail-card__actions">
                    <a href="{}"
                       target="_blank"
                       rel="noopener"
                       class="participant-detail-card__button">
                        Otevřít aktivační stránku →
                    </a>

                    <button
                        type="button"
                        class="participant-detail-card__button
                               participant-detail-card__button--secondary"
                        onclick="navigator.clipboard.writeText('{}');
                                 this.innerText='Zkopírováno';">
                        Kopírovat odkaz
                    </button>
                </div>
                """,
                activation_url,
                activation_url,
            )

        return self._render_detail_card(
            title="Aktivace",
            subtitle=(
                "Průběh aktivace účastníka a vytvoření přístupu."
            ),
            badge_label=status_label,
            badge_class=status_class,
            items=(
                (
                    "Stav aktivace",
                    status_value,
                ),
                (
                    "Aktivační odkaz odeslán",
                    self._format_admin_datetime(
                        obj.activation_sent_at
                    ),
                ),
                (
                    "Aktivace dokončena",
                    self._format_admin_datetime(
                        obj.activation_completed_at
                    ),
                ),
            ),
            actions=activation_action,
        )

    @admin.display(description="Pracovní souhrn")
    def participant_dashboard(self, obj):
        if not obj or not obj.pk:
            return "Pracovní souhrn bude dostupný po uložení účastníka."

        order = obj.order

        full_name = (
            f"{obj.first_name} {obj.last_name}".strip()
            or "—"
        )

        registration_number = (
            obj.registration_number
            or "Bez evidenčního čísla"
        )

        is_paid = (
            order.status == "paid"
            if order
            else False
        )

        if is_paid:
            payment_label = "Zaplaceno"
            payment_class = "status-success"
        else:
            payment_label = "Čeká na platbu"
            payment_class = "status-warning"

        order_card = self._render_dashboard_card(
            "Objednávka",
            f"#{order.pk}" if order else "—",
            payment_label,
            payment_class,
        )

        if not is_paid:
            activation_value = "—"
            activation_label = "Čeká na platbu"
            activation_class = "status-neutral"

        elif obj.activation_completed_at:
            activation_value = self._format_admin_datetime(
                obj.activation_completed_at
            )
            activation_label = "Aktivováno"
            activation_class = "status-success"

        elif obj.activation_sent_at:
            activation_value = (
                "Odesláno "
                + self._format_admin_datetime(
                    obj.activation_sent_at
                )
            )
            activation_label = "Čeká na aktivaci"
            activation_class = "status-warning"

        elif obj.activation_token:
            activation_value = "Odkaz připraven"
            activation_label = "Čeká na aktivaci"
            activation_class = "status-warning"

        else:
            activation_value = "Bez odkazu"
            activation_label = "Čeká na aktivaci"
            activation_class = "status-warning"

        activation_card = self._render_dashboard_card(
            "Aktivace",
            activation_value,
            activation_label,
            activation_class,
            small_value=True,
        )

        if obj.user_id:
            account_value = (
                obj.user.email
                or obj.user.username
                or f"ID {obj.user_id}"
            )
            account_label = "Existuje"
            account_class = "status-success"

        else:
            account_value = "Bez účtu"

            if obj.activation_completed_at:
                account_label = "Chybí účet"
                account_class = "status-danger"
            else:
                account_label = "Nevytvořen"
                account_class = "status-neutral"

        account_card = self._render_dashboard_card(
            "Uživatelský účet",
            account_value,
            account_label,
            account_class,
            small_value=True,
        )

        if not obj.user_id:
            quiz_value = "Nezahájen"
            quiz_label = "Nedostupný"
            quiz_class = "status-neutral"

        elif obj.admin_has_passed_quiz:
            quiz_value = (
                f"{obj.admin_latest_score} %"
                if obj.admin_latest_score is not None
                else "Splněn"
            )
            quiz_label = "Splněn"
            quiz_class = "status-success"

        elif obj.admin_has_submitted_quiz:
            quiz_value = (
                f"{obj.admin_latest_score} %"
                if obj.admin_latest_score is not None
                else "Nesplněn"
            )
            quiz_label = "Nesplněn"
            quiz_class = "status-danger"

        elif obj.admin_has_in_progress_quiz:
            quiz_value = "Probíhá"
            quiz_label = "Rozpracovaný"
            quiz_class = "status-info"

        else:
            quiz_value = "Nezahájen"
            quiz_label = "Nezahájen"
            quiz_class = "status-neutral"

        quiz_card = self._render_dashboard_card(
            "Test",
            quiz_value,
            quiz_label,
            quiz_class,
        )

        try:
            certificate = obj.certificate
        except Certificate.DoesNotExist:
            certificate = None

        if certificate:
            certificate_value = (
                certificate.certificate_number
                or "Bez čísla"
            )
            certificate_label = "Vystaven"
            certificate_class = "status-success"

        else:
            certificate_value = "Nevystaven"

            if obj.admin_has_passed_quiz:
                certificate_label = "Čeká na vystavení"
                certificate_class = "status-warning"
            else:
                certificate_label = "Nevystaven"
                certificate_class = "status-neutral"

        certificate_card = self._render_dashboard_card(
            "Certifikát",
            certificate_value,
            certificate_label,
            certificate_class,
            small_value=True,
        )

        course_name = (
            order.get_course_type_display()
            if order
            else "—"
        )

        company_name = (
            order.company_name
            if order and order.company_name
            else "—"
        )

        return format_html(
            """
            <div class="participant-dashboard">

                <div class="participant-dashboard__identity">

                    <div class="participant-dashboard__registration">
                        {}
                    </div>

                    <div class="participant-dashboard__name">
                        {}
                    </div>

                    <div class="participant-dashboard__email">
                        {}
                    </div>

                </div>

                <div class="participant-dashboard__cards">
                    {}
                    {}
                    {}
                    {}
                    {}
                </div>

                <div class="participant-dashboard__meta">

                    <span>
                        Kurz:
                        <strong>{}</strong>
                    </span>

                    <span>
                        Firma:
                        <strong>{}</strong>
                    </span>

                    <span>
                        Objednávka vytvořena:
                        <strong>{}</strong>
                    </span>

                    <span>
                        Zaplaceno:
                        <strong>{}</strong>
                    </span>

                </div>

            </div>
            """,
            registration_number,
            full_name,
            obj.email or "—",
            order_card,
            activation_card,
            account_card,
            quiz_card,
            certificate_card,
            course_name,
            company_name,
            self._format_admin_datetime(
                order.created_at
                if order
                else None
            ),
            self._format_admin_datetime(
                order.paid_at
                if order
                else None
            ),
        )

    @admin.display(
        description="Evidenční číslo",
        ordering="registration_number",
    )
    def registration_number_display(self, obj):
        return obj.registration_number or "—"

    @admin.display(
        description="Účastník",
        ordering="last_name",
    )
    def participant_name(self, obj):
        return f"{obj.last_name} {obj.first_name}".strip()

    @admin.display(
        description="Kurz",
        ordering="order__course_type",
    )
    def course_display(self, obj):
        return obj.order.get_course_type_display()

    @admin.display(
        description="Objednatel",
        ordering="order__company_name",
    )
    def company_display(self, obj):
        return obj.order.company_name or "—"

    @admin.display(
        boolean=True,
        description="Zaplaceno",
        ordering="order__status",
    )
    def payment_status(self, obj):
        return obj.order.status == "paid"

    @admin.display(
        boolean=True,
        description="Aktivace",
        ordering="activation_completed_at",
    )
    def activation_status(self, obj):
        return bool(obj.activation_completed_at)

    @admin.display(
        boolean=True,
        description="Účet",
        ordering="user",
    )
    def account_status(self, obj):
        return obj.user_id is not None

    @admin.display(
        boolean=True,
        description="Profil",
        ordering="admin_has_profile",
    )
    def profile_status(self, obj):
        return obj.admin_has_profile

    @admin.display(
        description="Test",
        ordering="admin_latest_score",
    )
    def quiz_status(self, obj):
        if not obj.user_id:
            return "—"

        if obj.admin_has_passed_quiz:
            if obj.admin_latest_score is not None:
                return f"Splněn ({obj.admin_latest_score} %)"

            return "Splněn"

        if obj.admin_has_submitted_quiz:
            if obj.admin_latest_score is not None:
                return f"Nesplněn ({obj.admin_latest_score} %)"

            return "Nesplněn"

        if obj.admin_has_in_progress_quiz:
            return "Rozpracovaný"

        return "Nezahájen"

    @admin.display(
        boolean=True,
        description="Certifikát",
        ordering="admin_has_certificate",
    )
    def certificate_status(self, obj):
        return obj.admin_has_certificate

    @admin.display(description="Aktivační odkaz")
    def activation_link(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        if obj.activation_completed_at:
            return "Aktivace byla dokončena."

        if obj.user_id:
            return (
                "Účastník již má uživatelský účet. "
                "Aktivační odkaz nelze obnovit."
            )

        if not obj.activation_token:
            return (
                "Aktivační token není vytvořen. "
                "Použijte administrační akci pro jeho vygenerování."
            )

        relative_url = reverse(
            "participant_activation",
            args=[obj.activation_token],
        )

        request = getattr(self, "_current_request", None)

        if request:
            activation_url = request.build_absolute_uri(relative_url)
        else:
            activation_url = relative_url

        return format_html(
            (
                '<a href="{}" target="_blank" rel="noopener">'
                "Otevřít aktivační stránku"
                "</a>"
                "<br>"
                '<code id="activation-link-{}">{}</code>'
                "<br>"
                '<button type="button" '
                'onclick="navigator.clipboard.writeText('
                "document.getElementById('activation-link-{}').innerText"
                '); this.innerText=\'Zkopírováno\';">'
                "Kopírovat odkaz"
                "</button>"
            ),
            activation_url,
            obj.pk,
            activation_url,
            obj.pk,
        )

    def get_form(self, request, obj=None, **kwargs):
        self._current_request = request
        return super().get_form(request, obj, **kwargs)

    @admin.display(description="Uživatelský účet")
    def account_link(self, obj):
        if not obj or not obj.user_id:
            return "Uživatelský účet zatím neexistuje."

        url = reverse(
            "admin:courses_customuser_change",
            args=[obj.user_id],
        )

        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user,
        )

    @admin.display(description="")
    def profile_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        try:
            profile = obj.profile
        except ParticipantProfile.DoesNotExist:
            return self._render_detail_card(
                title="Profil účastníka",
                subtitle="Osobní údaje zatím nebyly vyplněny.",
                badge_label="Chybí profil",
                badge_class="status-warning",
            )

        url = reverse(
            "admin:courses_participantprofile_change",
            args=[profile.pk],
        )

        birth_date = (
            profile.birth_date.strftime("%d.%m.%Y")
            if profile.birth_date
            else "—"
        )

        return self._render_detail_card(
            title="Profil účastníka",
            subtitle="Osobní a zaměstnanecké údaje",
            badge_label="Vyplněn",
            badge_class="status-success",
            items=(
                (
                    "Datum narození",
                    birth_date,
                ),
                (
                    "Místo narození",
                    profile.birth_place or "—",
                ),
                (
                    "Trvalé bydliště",
                    profile.permanent_address or "—",
                ),
                (
                    "Zaměstnavatel",
                    profile.employer_name or "—",
                ),
                (
                    "Adresa zaměstnavatele",
                    profile.employer_address or "—",
                ),
            ),
            actions=self._render_detail_link(
                url,
                "Otevřít profil →",
            ),
        )

    @admin.display(description="")
    def quiz_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        if not obj.user_id:
            return self._render_detail_card(
                title="Historie testů",
                subtitle=(
                    "Test zatím není dostupný, protože "
                    "účastník nemá uživatelský účet."
                ),
                badge_label="Nedostupné",
                badge_class="status-neutral",
            )

        attempts = list(
            obj.user.quiz_attempts
            .select_related("course")
            .order_by(
                "-started_at",
                "-pk",
            )
        )

        if not attempts:
            return self._render_detail_card(
                title="Historie testů",
                subtitle="Účastník zatím nezahájil žádný test.",
                badge_label="Bez pokusů",
                badge_class="status-neutral",
            )

        rows = []

        for attempt in attempts:
            detail_url = reverse(
                "admin:courses_quizattempt_change",
                args=[attempt.pk],
            )

            if attempt.status == QuizAttempt.STATUS_IN_PROGRESS:
                status = self._render_detail_badge(
                    "Rozpracovaný",
                    "status-info",
                )
                score = "—"

            elif attempt.passed:
                status = self._render_detail_badge(
                    "Splněn",
                    "status-success",
                )
                score = f"{attempt.score_percent} %"

            else:
                status = self._render_detail_badge(
                    "Nesplněn",
                    "status-danger",
                )
                score = f"{attempt.score_percent} %"

            rows.append(
                format_html(
                    """
                    <tr>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td class="participant-test-history__action">
                            <a href="{}"
                               class="participant-detail-card__button">
                                Detail →
                            </a>
                        </td>
                    </tr>
                    """,
                    attempt.attempt_number,
                    self._format_admin_datetime(
                        attempt.started_at
                    ),
                    self._format_admin_datetime(
                        attempt.submitted_at
                    ),
                    status,
                    score,
                    detail_url,
                )
            )

        body = format_html_join(
            "",
            "{}",
            ((row,) for row in rows),
        )

        table = format_html(
            """
            <div class="participant-test-history">
                <table>
                    <thead>
                        <tr>
                            <th>Pokus</th>
                            <th>Zahájeno</th>
                            <th>Odesláno</th>
                            <th>Výsledek</th>
                            <th>Skóre</th>
                            <th></th>
                        </tr>
                    </thead>

                    <tbody>
                        {}
                    </tbody>
                </table>
            </div>
            """,
            body,
        )

        return self._render_detail_card(
            title="Historie testů",
            subtitle="Všechny testové pokusy tohoto účastníka.",
            badge_label=f"{len(attempts)} pokusů",
            badge_class="status-info",
            body=table,
        )

    @admin.display(description="")
    def certificate_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        try:
            certificate = obj.certificate
        except Certificate.DoesNotExist:
            certificate = None

        if certificate is None:
            return self._render_detail_card(
                title="Certifikát",
                subtitle="Certifikát zatím nebyl vystaven.",
                badge_label="Nevystaven",
                badge_class="status-neutral",
            )

        detail_url = reverse(
            "admin:courses_certificate_change",
            args=[certificate.pk],
        )

        valid_until = (
            certificate.valid_until.strftime("%d.%m.%Y")
            if certificate.valid_until
            else "—"
        )

        is_valid = (
            certificate.valid_until
            and certificate.valid_until >= timezone.localdate()
        )

        if is_valid:
            validity_label = "Platný"
            validity_class = "status-success"
        else:
            validity_label = "Neplatný"
            validity_class = "status-danger"

        return self._render_detail_card(
            title="Certifikát",
            subtitle="Vystavený certifikát účastníka.",
            badge_label=validity_label,
            badge_class=validity_class,
            items=(
                (
                    "Číslo certifikátu",
                    certificate.certificate_number or "—",
                ),
                (
                    "Vystaveno",
                    self._format_admin_datetime(
                        certificate.issued_at
                    ),
                ),
                (
                    "Platnost do",
                    valid_until,
                ),
            ),
            actions=self._render_detail_link(
                detail_url,
                "Otevřít certifikát →",
            ),
        )

    @admin.display(description="")
    def email_history_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        email_filter = Q(
            order_id=obj.order_id,
            recipient__iexact=obj.email,
        )

        if obj.user_id:
            email_filter |= Q(
                quiz_attempt__user_id=obj.user_id,
            )

        logs = list(
            EmailLog.objects
            .filter(email_filter)
            .select_related(
                "order",
                "quiz_attempt",
            )
            .order_by(
                "-created_at",
                "-pk",
            )[:20]
        )

        if not logs:
            return self._render_detail_card(
                title="E-mailová historie",
                subtitle=(
                    "K tomuto účastníkovi zatím nejsou "
                    "evidovány žádné e-maily."
                ),
                badge_label="Bez záznamů",
                badge_class="status-neutral",
            )

        rows = []

        for log in logs:
            detail_url = reverse(
                "admin:courses_emaillog_change",
                args=[log.pk],
            )

            if log.status == EmailLog.STATUS_SENT:
                status = self._render_detail_badge(
                    "Odesláno",
                    "status-success",
                )

            elif log.status == EmailLog.STATUS_FAILED:
                status = self._render_detail_badge(
                    "Chyba",
                    "status-danger",
                )

            else:
                status = self._render_detail_badge(
                    "Náhled",
                    "status-neutral",
                )

            rows.append(
                format_html(
                    """
                    <tr>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>

                        <td class="participant-email-history__action">
                            <a href="{}"
                               class="participant-detail-card__button">
                                Detail →
                            </a>
                        </td>
                    </tr>
                    """,
                    self._format_admin_datetime(
                        log.created_at
                    ),
                    log.get_email_type_display(),
                    log.recipient,
                    status,
                    self._format_admin_datetime(
                        log.sent_at
                    ),
                    detail_url,
                )
            )

        body = format_html_join(
            "",
            "{}",
            ((row,) for row in rows),
        )

        table = format_html(
            """
            <div class="participant-email-history">
                <table>
                    <thead>
                        <tr>
                            <th>Vytvořeno</th>
                            <th>Typ</th>
                            <th>Příjemce</th>
                            <th>Stav</th>
                            <th>Odesláno</th>
                            <th></th>
                        </tr>
                    </thead>

                    <tbody>
                        {}
                    </tbody>
                </table>
            </div>
            """,
            body,
        )

        return self._render_detail_card(
            title="E-mailová historie",
            subtitle="E-maily související s tímto účastníkem.",
            badge_label=f"{len(logs)} záznamů",
            badge_class="status-info",
            body=table,
        )

    @admin.action(
        description="Vygenerovat nový aktivační odkaz"
    )
    def regenerate_activation_tokens(
        self,
        request,
        queryset,
    ):
        regenerated_count = 0
        activated_count = 0
        account_exists_count = 0

        participant_ids = list(
            queryset.values_list("pk", flat=True)
        )

        with transaction.atomic():
            participants = (
                OrderParticipant.objects
                .select_for_update()
                .filter(pk__in=participant_ids)
                .order_by("pk")
            )

            for participant in participants:
                if participant.activation_completed_at:
                    activated_count += 1
                    continue

                if participant.user_id:
                    account_exists_count += 1
                    continue

                participant.activation_token = uuid.uuid4()
                participant.activation_sent_at = None
                participant.save(
                    update_fields=(
                        "activation_token",
                        "activation_sent_at",
                    )
                )

                regenerated_count += 1

        if regenerated_count:
            self.message_user(
                request,
                (
                    "Nový aktivační odkaz byl vygenerován "
                    f"pro {regenerated_count} účastníků."
                ),
                level=messages.SUCCESS,
            )

        if activated_count:
            self.message_user(
                request,
                (
                    f"{activated_count} účastníků již dokončilo "
                    "aktivaci. Jejich token nebyl změněn."
                ),
                level=messages.WARNING,
            )

        if account_exists_count:
            self.message_user(
                request,
                (
                    f"{account_exists_count} účastníků již má "
                    "uživatelský účet. Jejich token nebyl změněn."
                ),
                level=messages.WARNING,
            )

    @admin.action(
        description="Exportovat vybrané účastníky do CSV"
    )
    def export_participants_to_csv(
        self,
        request,
        queryset,
    ):
        response = HttpResponse(
            content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="ucastnici.csv"'
        )

        response.write("\ufeff")
        writer = csv.writer(
            response,
            delimiter=";",
            lineterminator="\n",
        )

        writer.writerow(
            (
                "Evidenční číslo",
                "Jméno",
                "Příjmení",
                "E-mail",
                "Kurz",
                "Objednávka",
                "Objednatel",
                "IČO",
                "Zaplaceno",
                "Aktivováno",
                "Uživatelský účet",
                "Profil vyplněn",
                "Stav testu",
                "Poslední skóre",
                "Certifikát vystaven",
                "Číslo certifikátu",
                "Platnost certifikátu",
            )
        )

        participants = (
            queryset
            .select_related(
                "order",
                "user",
            )
            .order_by(
                "last_name",
                "first_name",
            )
        )

        for participant in participants:
            try:
                profile_exists = bool(participant.profile)
            except ParticipantProfile.DoesNotExist:
                profile_exists = False

            try:
                certificate = participant.certificate
            except Certificate.DoesNotExist:
                certificate = None

            latest_attempt = None
            if participant.user_id:
                latest_attempt = (
                    QuizAttempt.objects
                    .filter(user_id=participant.user_id)
                    .order_by("-started_at")
                    .first()
                )

            if not latest_attempt:
                quiz_status = "Nezahájen"
                latest_score = ""
            elif (
                latest_attempt.status
                == QuizAttempt.STATUS_IN_PROGRESS
            ):
                quiz_status = "Rozpracovaný"
                latest_score = ""
            elif latest_attempt.passed:
                quiz_status = "Splněn"
                latest_score = latest_attempt.score_percent
            else:
                quiz_status = "Nesplněn"
                latest_score = latest_attempt.score_percent

            writer.writerow(
                (
                    participant.registration_number or "",
                    participant.first_name or "",
                    participant.last_name or "",
                    participant.email or "",
                    participant.order.get_course_type_display(),
                    participant.order_id,
                    participant.order.company_name or "",
                    participant.order.ico or "",
                    (
                        "Ano"
                        if participant.order.status == "paid"
                        else "Ne"
                    ),
                    (
                        "Ano"
                        if participant.activation_completed_at
                        else "Ne"
                    ),
                    "Ano" if participant.user_id else "Ne",
                    "Ano" if profile_exists else "Ne",
                    quiz_status,
                    latest_score,
                    "Ano" if certificate else "Ne",
                    (
                        certificate.certificate_number
                        if certificate
                        else ""
                    ),
                    (
                        certificate.valid_until
                        if certificate
                        else ""
                    ),
                )
            )

        return response



@admin.register(ParticipantProfile)
class ParticipantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "birth_date",
        "birth_place",
        "employer_name",
        "created_at",
    )

    search_fields = (
        "participant__registration_number",
        "participant__first_name",
        "participant__last_name",
        "participant__email",
        "birth_place",
        "permanent_address",
        "employer_name",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "participant",
    )

    readonly_fields = (
        "created_at",
    )

    list_select_related = (
        "participant",
    )

    ordering = (
        "-created_at",
    )


class QuizAttemptQuestionInline(admin.TabularInline):
    model = QuizAttemptQuestion
    extra = 0
    can_delete = False
    show_change_link = False

    fields = (
        "order",
        "question_text",
        "selected_choice_text",
        "answer_status",
    )

    readonly_fields = (
        "order",
        "question_text",
        "selected_choice_text",
        "answer_status",
    )

    ordering = ("order",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False

    @admin.display(description="Otázka")
    def question_text(self, obj):
        if not obj or not obj.question_id:
            return "—"

        return obj.question.text

    @admin.display(description="Vybraná odpověď")
    def selected_choice_text(self, obj):
        if not obj or not obj.selected_choice_id:
            return "Nezodpovězeno"

        return obj.selected_choice.text

    @admin.display(
        boolean=True,
        description="Správně",
    )
    def answer_status(self, obj):
        if not obj or not obj.selected_choice_id:
            return False

        return bool(obj.selected_choice.is_correct)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "question",
                "selected_choice",
            )
        )


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": (
                "courses/admin/quiz_attempt_detail.css",
            )
        }

    list_display = (
        "id",
        "participant_name",
        "registration_number",
        "course",
        "attempt_number",
        "status_display",
        "result_display",
        "score_display",
        "duration_display",
        "started_at",
        "submitted_at",
    )

    list_display_links = (
        "id",
        "participant_name",
    )

    list_filter = (
        "status",
        "passed",
        "course",
        "started_at",
        "submitted_at",
    )

    search_fields = (
        "=id",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "course__title",
    )

    readonly_fields = (
        "attempt_dashboard",
        "user",
        "participant_link",
        "registration_number_detail",
        "course",
        "attempt_number",
        "status",
        "started_at",
        "submitted_at",
        "total_questions",
        "correct_answers",
        "score_percent",
        "passed",
        "duration_detail",
    )

    fieldsets = (
        (
            "Pracovní souhrn",
            {
                "fields": (
                    "attempt_dashboard",
                ),
                "classes": (
                    "quiz-attempt-dashboard-fieldset",
                ),
            },
        ),
        (
            "Účastník",
            {
                "fields": (
                    "user",
                    "participant_link",
                    "registration_number_detail",
                    "course",
                    "attempt_number",
                ),
            },
        ),
        (
            "Výsledek testu",
            {
                "fields": (
                    "status",
                    "passed",
                    (
                        "correct_answers",
                        "total_questions",
                    ),
                    "score_percent",
                ),
            },
        ),
        (
            "Časový průběh",
            {
                "fields": (
                    "started_at",
                    "submitted_at",
                    "duration_detail",
                ),
            },
        ),
    )

    inlines = [
        QuizAttemptQuestionInline,
    ]

    list_select_related = (
        "user",
        "course",
    )

    ordering = (
        "-started_at",
    )

    date_hierarchy = "started_at"
    list_per_page = 50
    save_on_top = True

    actions = (
        "export_quiz_attempts_to_csv",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.select_related(
            "user",
            "course",
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return True

    @staticmethod
    def _format_admin_datetime(value):
        if not value:
            return "—"

        return timezone.localtime(
            value
        ).strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _render_dashboard_badge(label, css_class):
        return format_html(
            (
                '<span class="quiz-attempt-dashboard__badge {}">'
                "{}"
                "</span>"
            ),
            css_class,
            label,
        )

    @staticmethod
    def _render_dashboard_card(
        label,
        value,
        *,
        badge_label=None,
        badge_class="status-neutral",
        small_value=False,
    ):
        value_class = (
            "quiz-attempt-dashboard__card-value "
            "quiz-attempt-dashboard__card-value--small"
            if small_value
            else "quiz-attempt-dashboard__card-value"
        )

        badge = ""
        if badge_label:
            badge = QuizAttemptAdmin._render_dashboard_badge(
                badge_label,
                badge_class,
            )

        return format_html(
            """
            <div class="quiz-attempt-dashboard__card">
                <div class="quiz-attempt-dashboard__card-label">
                    {}
                </div>
                <div class="{}">
                    {}
                </div>
                {}
            </div>
            """,
            label,
            value_class,
            value,
            badge,
        )

    @staticmethod
    def _render_dashboard_action(url, label, *, secondary=False):
        css_class = "quiz-attempt-dashboard__button"
        if secondary:
            css_class += " quiz-attempt-dashboard__button--secondary"

        return format_html(
            '<a href="{}" class="{}">{}</a>',
            url,
            css_class,
            label,
        )

    @admin.display(description="")
    def attempt_dashboard(self, obj):
        if not obj or not obj.pk:
            return "Souhrn bude dostupný po vytvoření testového pokusu."

        participant = self.get_participant(obj)
        full_name = obj.user.get_full_name().strip()
        if not full_name:
            full_name = obj.user.email or obj.user.username

        registration_number = (
            participant.registration_number
            if participant and participant.registration_number
            else "—"
        )

        if obj.status == QuizAttempt.STATUS_IN_PROGRESS:
            result_label = "Rozpracovaný"
            result_class = "status-info"
            score_value = "—"
            answers_value = (
                f"{obj.correct_answers} / {obj.total_questions}"
                if obj.total_questions
                else "—"
            )
        elif obj.passed:
            result_label = "Splněn"
            result_class = "status-success"
            score_value = (
                f"{obj.score_percent} %"
                if obj.score_percent is not None
                else "—"
            )
            answers_value = (
                f"{obj.correct_answers} / {obj.total_questions}"
            )
        else:
            result_label = "Nesplněn"
            result_class = "status-danger"
            score_value = (
                f"{obj.score_percent} %"
                if obj.score_percent is not None
                else "—"
            )
            answers_value = (
                f"{obj.correct_answers} / {obj.total_questions}"
            )

        participant_value = format_html(
            "{}<span class=\"quiz-attempt-dashboard__subvalue\">{}</span>",
            full_name,
            registration_number,
        )

        cards = format_html_join(
            "",
            "{}",
            (
                (
                    self._render_dashboard_card(
                        "Účastník",
                        participant_value,
                        badge_label=(
                            "Napojen na objednávku"
                            if participant
                            else "Bez vazby na účastníka"
                        ),
                        badge_class=(
                            "status-success"
                            if participant
                            else "status-warning"
                        ),
                        small_value=True,
                    ),
                ),
                (
                    self._render_dashboard_card(
                        "Kurz",
                        obj.course.title,
                        badge_label=f"Pokus č. {obj.attempt_number}",
                        badge_class="status-neutral",
                        small_value=True,
                    ),
                ),
                (
                    self._render_dashboard_card(
                        "Výsledek",
                        result_label,
                        badge_label=obj.get_status_display(),
                        badge_class=result_class,
                    ),
                ),
                (
                    self._render_dashboard_card(
                        "Skóre",
                        score_value,
                        badge_label=f"Správně {answers_value}",
                        badge_class=result_class,
                    ),
                ),
                (
                    self._render_dashboard_card(
                        "Délka testu",
                        self.format_duration(obj),
                        badge_label=(
                            "Dokončeno"
                            if obj.submitted_at
                            else "Probíhá"
                        ),
                        badge_class=(
                            "status-success"
                            if obj.submitted_at
                            else "status-info"
                        ),
                    ),
                ),
            ),
        )

        actions = []

        if participant:
            participant_url = reverse(
                "admin:courses_orderparticipant_change",
                args=[participant.pk],
            )
            actions.append(
                self._render_dashboard_action(
                    participant_url,
                    "Otevřít účastníka →",
                )
            )

        user_url = reverse(
            "admin:courses_customuser_change",
            args=[obj.user_id],
        )
        actions.append(
            self._render_dashboard_action(
                user_url,
                "Uživatelský účet →",
                secondary=True,
            )
        )

        actions_html = format_html_join(
            "",
            "{}",
            ((action,) for action in actions),
        )

        return format_html(
            """
            <div class="quiz-attempt-dashboard">

                <div class="quiz-attempt-dashboard__identity">
                    <div class="quiz-attempt-dashboard__eyebrow">
                        Pokus testu #{}
                    </div>
                    <div class="quiz-attempt-dashboard__name">
                        {}
                    </div>
                    <div class="quiz-attempt-dashboard__email">
                        {}
                    </div>
                </div>

                <div class="quiz-attempt-dashboard__cards">
                    {}
                </div>

                <div class="quiz-attempt-dashboard__meta">
                    <span>
                        Zahájeno:
                        <strong>{}</strong>
                    </span>
                    <span>
                        Odesláno:
                        <strong>{}</strong>
                    </span>
                    <span>
                        Kurz:
                        <strong>{}</strong>
                    </span>
                </div>

                <div class="quiz-attempt-dashboard__actions">
                    {}
                </div>

            </div>
            """,
            obj.pk,
            full_name,
            obj.user.email or "—",
            cards,
            self._format_admin_datetime(obj.started_at),
            self._format_admin_datetime(obj.submitted_at),
            obj.course.title,
            actions_html,
        )

    @admin.display(
        description="Účastník",
        ordering="user__last_name",
    )
    def participant_name(self, obj):
        full_name = obj.user.get_full_name().strip()

        if full_name:
            return full_name

        return obj.user.email or obj.user.username

    @admin.display(description="Evidenční číslo")
    def registration_number(self, obj):
        participant = self.get_participant(obj)

        if not participant:
            return "—"

        return participant.registration_number or "—"

    @admin.display(
        description="Stav",
        ordering="status",
    )
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.display(
        description="Výsledek",
        ordering="passed",
    )
    def result_display(self, obj):
        if obj.status == QuizAttempt.STATUS_IN_PROGRESS:
            return "Rozpracovaný"

        if obj.passed:
            return "Splněn"

        return "Nesplněn"

    @admin.display(
        description="Skóre",
        ordering="score_percent",
    )
    def score_display(self, obj):
        if obj.status == QuizAttempt.STATUS_IN_PROGRESS:
            return "—"

        return f"{obj.score_percent} %"

    @admin.display(description="Délka testu")
    def duration_display(self, obj):
        return self.format_duration(obj)

    @admin.display(description="Účastník objednávky")
    def participant_link(self, obj):
        if not obj or not obj.pk:
            return "Test je nejprve nutné uložit."

        participant = self.get_participant(obj)

        if not participant:
            return (
                "K tomuto uživateli není připojen "
                "účastník objednávky."
            )

        url = reverse(
            (
                f"admin:{participant._meta.app_label}_"
                f"{participant._meta.model_name}_change"
            ),
            args=[participant.pk],
        )

        return format_html(
            '<a href="{}">{}</a>',
            url,
            participant,
        )

    @admin.display(description="Evidenční číslo")
    def registration_number_detail(self, obj):
        if not obj or not obj.pk:
            return "—"

        participant = self.get_participant(obj)

        if not participant:
            return "—"

        return participant.registration_number or "—"

    @admin.display(description="Délka testu")
    def duration_detail(self, obj):
        if not obj or not obj.pk:
            return "—"

        return self.format_duration(obj)

    def get_participant(self, obj):
        if not obj or not obj.user_id:
            return None

        return (
            OrderParticipant.objects
            .filter(user_id=obj.user_id)
            .select_related("order")
            .order_by(
                "-activation_completed_at",
                "-id",
            )
            .first()
        )

    @admin.action(
        description="Exportovat vybrané testové pokusy do CSV"
    )
    def export_quiz_attempts_to_csv(
        self,
        request,
        queryset,
    ):
        response = HttpResponse(
            content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="testove_pokusy.csv"'
        )
        response.write("\ufeff")

        writer = csv.writer(
            response,
            delimiter=";",
            lineterminator="\n",
        )

        writer.writerow(
            (
                "ID pokusu",
                "Evidenční číslo",
                "Účastník",
                "E-mail",
                "Kurz",
                "Číslo pokusu",
                "Stav",
                "Výsledek",
                "Správné odpovědi",
                "Počet otázek",
                "Skóre (%)",
                "Zahájeno",
                "Odesláno",
                "Délka testu",
            )
        )

        attempts = list(
            queryset
            .select_related(
                "user",
                "course",
            )
            .order_by("-started_at")
        )

        user_ids = {
            attempt.user_id
            for attempt in attempts
        }

        participants = (
            OrderParticipant.objects
            .filter(user_id__in=user_ids)
            .select_related("order")
            .order_by(
                "user_id",
                "-activation_completed_at",
                "-id",
            )
        )

        participant_map = {}
        for participant in participants:
            participant_map.setdefault(
                participant.user_id,
                participant,
            )

        for attempt in attempts:
            participant = participant_map.get(
                attempt.user_id
            )

            full_name = attempt.user.get_full_name().strip()
            if not full_name:
                full_name = (
                    attempt.user.email
                    or attempt.user.username
                )

            if (
                attempt.status
                == QuizAttempt.STATUS_IN_PROGRESS
            ):
                result = "Rozpracovaný"
            elif attempt.passed:
                result = "Splněn"
            else:
                result = "Nesplněn"

            writer.writerow(
                (
                    attempt.pk,
                    (
                        participant.registration_number
                        if participant
                        else ""
                    ),
                    full_name,
                    attempt.user.email or "",
                    attempt.course.title,
                    attempt.attempt_number,
                    attempt.get_status_display(),
                    result,
                    attempt.correct_answers,
                    attempt.total_questions,
                    attempt.score_percent,
                    attempt.started_at,
                    attempt.submitted_at or "",
                    self.format_duration(attempt),
                )
            )

        return response

    def format_duration(self, obj):
        if not obj.started_at:
            return "—"

        end_time = obj.submitted_at

        if not end_time:
            return "Probíhá"

        duration = end_time - obj.started_at
        total_seconds = max(
            0,
            int(duration.total_seconds()),
        )

        hours, remainder = divmod(
            total_seconds,
            3600,
        )
        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours:d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return f"{minutes:d}:{seconds:02d}"
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number",
        "participant",
        "quiz_attempt",
        "issued_at",
        "valid_until",
        "is_valid",
    )

    list_display_links = (
        "certificate_number",
        "participant",
    )

    list_filter = (
        "issued_at",
        "valid_until",
        "quiz_attempt__course",
    )

    search_fields = (
        "certificate_number",
        "participant__registration_number",
        "participant__first_name",
        "participant__last_name",
        "participant__email",
        "quiz_attempt__user__email",
    )

    readonly_fields = (
        "verification_token",
        "created_at",
    )

    autocomplete_fields = (
        "participant",
        "quiz_attempt",
    )

    list_select_related = (
        "participant",
        "quiz_attempt",
        "quiz_attempt__course",
    )

    ordering = (
        "-issued_at",
    )

    date_hierarchy = "issued_at"
    list_per_page = 50
    save_on_top = True

    @admin.display(
        boolean=True,
        description="Platné",
        ordering="valid_until",
    )
    def is_valid(self, obj):
        return obj.valid_until >= timezone.localdate()

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at_display",
        "email_type_display",
        "recipient_display",
        "status_display",
        "order_link",
        "quiz_attempt_link",
        "sent_at_display",
        "preview_list_link",
    )

    list_display_links = (
        "created_at_display",
        "recipient_display",
    )

    list_filter = (
        "email_type",
        "status",
        "created_at",
        "sent_at",
    )

    search_fields = (
        "recipient",
        "subject",
        "=order__id",
        "=quiz_attempt__id",
        "quiz_attempt__user__email",
        "quiz_attempt__user__first_name",
        "quiz_attempt__user__last_name",
    )

    readonly_fields = (
        "email_type",
        "recipient",
        "subject",
        "status",
        "error_message",
        "order_link",
        "quiz_attempt_link",
        "created_at",
        "sent_at",
        "preview_link",
    )

    fieldsets = (
        (
            "E-mail",
            {
                "fields": (
                    "email_type",
                    "recipient",
                    "subject",
                    "status",
                    "created_at",
                    "sent_at",
                ),
            },
        ),
        (
            "Vazby",
            {
                "fields": (
                    "order_link",
                    "quiz_attempt_link",
                ),
            },
        ),
        (
            "Náhled",
            {
                "fields": (
                    "preview_link",
                ),
            },
        ),
        (
            "Chyba",
            {
                "fields": (
                    "error_message",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    ordering = (
        "-created_at",
        "-id",
    )

    date_hierarchy = "created_at"
    list_per_page = 50

    def has_view_permission(
        self,
        request,
        obj=None,
    ):
        return bool(
            request.user
            and request.user.is_active
            and request.user.is_staff
        )

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False

    @admin.display(
        description="Typ",
        ordering="email_type",
    )
    def email_type_display(self, obj):
        colors = {
            EmailLog.TYPE_PARTICIPANT_ACTIVATION: (
                "#0d6efd",
                "Aktivace účastníka",
            ),
            EmailLog.TYPE_PAYMENT_COMPLETED: (
                "#0f766e",
                "Platba přijata",
            ),
            EmailLog.TYPE_COURSE_COMPLETED: (
                "#7c3aed",
                "Dokončení kurzu",
            ),
        }

        color, label = colors.get(
            obj.email_type,
            (
                "#6c757d",
                obj.get_email_type_display(),
            ),
        )

        return format_html(
            (
                '<span style="'
                "display:inline-block;"
                "padding:3px 8px;"
                "border-radius:10px;"
                "background:{};"
                "color:#fff;"
                'font-weight:600;">'
                "{}"
                "</span>"
            ),
            color,
            label,
        )

    @admin.display(
        description="Datum",
        ordering="created_at",
    )
    def created_at_display(self, obj):
        return timezone.localtime(
            obj.created_at
        ).strftime("%d. %m. %Y %H:%M")

    @admin.display(
        description="Příjemce",
        ordering="recipient",
    )
    def recipient_display(self, obj):
        return obj.recipient

    @admin.display(
        description="Odesláno",
        ordering="sent_at",
    )
    def sent_at_display(self, obj):
        if not obj.sent_at:
            return "—"

        return timezone.localtime(
            obj.sent_at
        ).strftime("%d. %m. %Y %H:%M")

    @admin.display(description="Náhled")
    def preview_list_link(self, obj):
        if not obj or not obj.pk:
            return "—"

        if (
            obj.email_type == EmailLog.TYPE_PAYMENT_COMPLETED
            and obj.order_id
        ):
            url = reverse(
                "payment_completed_email_preview",
                kwargs={
                    "order_id": obj.order_id,
                },
            )

        elif (
            obj.email_type == EmailLog.TYPE_COURSE_COMPLETED
            and obj.quiz_attempt_id
        ):
            url = reverse(
                "course_completed_email_preview",
                kwargs={
                    "attempt_id": obj.quiz_attempt_id,
                },
            )

        elif (
            obj.email_type == EmailLog.TYPE_PARTICIPANT_ACTIVATION
            and obj.order_id
        ):
            participant = (
                obj.order.participants
                .filter(
                    email__iexact=obj.recipient,
                )
                .first()
            )

            if participant is None:
                return "Účastník nenalezen."

            url = reverse(
                "participant_activation_email_preview",
                kwargs={
                    "token": participant.activation_token,
                },
            )

        else:
            return "—"

        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Otevřít</a>',
            url,
        )

    @admin.display(
        description="Stav",
        ordering="status",
    )
    def status_display(self, obj):
        colors = {
            EmailLog.STATUS_PREVIEW: (
                "#6c757d",
                "Náhled",
            ),
            EmailLog.STATUS_SENT: (
                "#198754",
                "Odesláno",
            ),
            EmailLog.STATUS_FAILED: (
                "#dc3545",
                "Chyba",
            ),
        }

        color, label = colors.get(
            obj.status,
            (
                "#6c757d",
                obj.get_status_display(),
            ),
        )

        return format_html(
            (
                '<span style="'
                "display:inline-block;"
                "padding:3px 8px;"
                "border-radius:10px;"
                "background:{};"
                "color:#fff;"
                'font-weight:600;">'
                "{}"
                "</span>"
            ),
            color,
            label,
        )

    @admin.display(description="Objednávka")
    def order_link(self, obj):
        if not obj.order_id:
            return "—"

        url = reverse(
            "admin:courses_order_change",
            args=[obj.order_id],
        )

        return format_html(
            '<a href="{}">Objednávka #{}</a>',
            url,
            obj.order_id,
        )

    @admin.display(description="Pokus testu")
    def quiz_attempt_link(self, obj):
        if not obj.quiz_attempt_id:
            return "—"

        url = reverse(
            "admin:courses_quizattempt_change",
            args=[obj.quiz_attempt_id],
        )

        return format_html(
            '<a href="{}">Pokus #{}</a>',
            url,
            obj.quiz_attempt_id,
        )

    @admin.display(description="Náhled e-mailu")
    def preview_link(self, obj):
        if not obj or not obj.pk:
            return "—"

        if (
            obj.email_type
            == EmailLog.TYPE_PAYMENT_COMPLETED
            and obj.order_id
        ):
            url = reverse(
                "payment_completed_email_preview",
                kwargs={
                    "order_id": obj.order_id,
                },
            )

        elif (
            obj.email_type
            == EmailLog.TYPE_COURSE_COMPLETED
            and obj.quiz_attempt_id
        ):
            url = reverse(
                "course_completed_email_preview",
                kwargs={
                    "attempt_id": obj.quiz_attempt_id,
                },
            )

        elif (
            obj.email_type
            == EmailLog.TYPE_PARTICIPANT_ACTIVATION
            and obj.order_id
        ):
            participant = (
                obj.order.participants
                .filter(
                    email__iexact=obj.recipient,
                )
                .first()
            )

            if participant is None:
                return (
                    "Účastník pro tento e-mail "
                    "již nebyl nalezen."
                )

            url = reverse(
                "participant_activation_email_preview",
                kwargs={
                    "token": participant.activation_token,
                },
            )

        else:
            return "Náhled není dostupný."

        return format_html(
            (
                '<a href="{}" '
                'target="_blank" '
                'rel="noopener">'
                "Otevřít náhled"
                "</a>"
            ),
            url,
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "order",
                "quiz_attempt",
                "quiz_attempt__user",
            )
            .prefetch_related(
                "order__participants",
            )
        )



admin.site.site_header = "Elektroakademie – Administrace"
admin.site.site_title = "Elektroakademie"
admin.site.index_title = "Správa systému"
