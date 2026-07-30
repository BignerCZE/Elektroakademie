import uuid

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Certificate,
    Choice,
    Course,
    CustomUser,
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


class OrderParticipantInline(admin.TabularInline):
    model = OrderParticipant
    extra = 0
    show_change_link = True
    can_delete = False

    fields = (
        "registration_number",
        "first_name",
        "last_name",
        "email",
        "activation_status",
        "user",
    )

    readonly_fields = (
        "registration_number",
        "activation_status",
        "user",
    )

    ordering = (
        "last_name",
        "first_name",
    )

    @admin.display(
        boolean=True,
        description="Aktivován",
    )
    def activation_status(self, obj):
        if not obj or not obj.pk:
            return False

        return bool(obj.activation_completed_at)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
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
        "created_at",
        "paid_at",
        "participant_summary",
    )

    fieldsets = (
        (
            "Objednávka",
            {
                "fields": (
                    "course_type",
                    "status",
                    "total_price",
                    "created_at",
                    "paid_at",
                    "participant_summary",
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

    inlines = [OrderParticipantInline]

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
        "profile_summary",
        "quiz_summary",
        "certificate_summary",
    )

    fieldsets = (
        (
            "Účastník",
            {
                "fields": (
                    "order",
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
                    "user",
                    "account_link",
                    "activation_link",
                    "activation_token",
                    "activation_sent_at",
                    "activation_completed_at",
                ),
            },
        ),
        (
            "Navazující údaje",
            {
                "fields": (
                    "profile_summary",
                    "quiz_summary",
                    "certificate_summary",
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

    @admin.display(description="Profil účastníka")
    def profile_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        try:
            profile = obj.profile
        except ParticipantProfile.DoesNotExist:
            return "Profil zatím nebyl vyplněn."

        url = reverse(
            (
                f"admin:{profile._meta.app_label}_"
                f"{profile._meta.model_name}_change"
            ),
            args=[profile.pk],
        )

        return format_html(
            (
                '<a href="{}">Otevřít profil</a>'
                "<br>"
                "Datum narození: {}"
                "<br>"
                "Místo narození: {}"
                "<br>"
                "Trvalé bydliště: {}"
            ),
            url,
            profile.birth_date,
            profile.birth_place,
            profile.permanent_address,
        )

    @admin.display(description="Test")
    def quiz_summary(self, obj):
        if not obj or not obj.user_id:
            return "Účastník zatím nemá uživatelský účet."

        latest_attempt = (
            obj.user.quiz_attempts
            .order_by("-started_at")
            .first()
        )

        if not latest_attempt:
            return "Test zatím nebyl zahájen."

        url = reverse(
            "admin:courses_quizattempt_change",
            args=[latest_attempt.pk],
        )

        if latest_attempt.status == QuizAttempt.STATUS_IN_PROGRESS:
            result = "Rozpracovaný"
        elif latest_attempt.passed:
            result = f"Splněn – {latest_attempt.score_percent} %"
        else:
            result = f"Nesplněn – {latest_attempt.score_percent} %"

        return format_html(
            (
                '<a href="{}">Otevřít poslední pokus</a>'
                "<br>"
                "Pokus č. {}"
                "<br>"
                "Výsledek: {}"
            ),
            url,
            latest_attempt.attempt_number,
            result,
        )

    @admin.display(description="Certifikát")
    def certificate_summary(self, obj):
        if not obj or not obj.pk:
            return "Účastníka je nejprve nutné uložit."

        try:
            certificate = obj.certificate
        except Certificate.DoesNotExist:
            return "Certifikát zatím nebyl vystaven."

        url = reverse(
            "admin:courses_certificate_change",
            args=[certificate.pk],
        )

        return format_html(
            (
                '<a href="{}">Otevřít certifikát</a>'
                "<br>"
                "Číslo: {}"
                "<br>"
                "Platnost do: {}"
            ),
            url,
            certificate.certificate_number,
            certificate.valid_until,
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
        return False

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
            .first()
        )

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