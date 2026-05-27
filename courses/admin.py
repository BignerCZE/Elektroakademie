from django.contrib import admin

from .models import (
    CustomUser,
    Course,
    QuestionCategory,
    Question,
    Choice,
    Payment,
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
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_paid", "passed_quiz")
    search_fields = ("username", "email")
    list_filter = ("is_paid", "passed_quiz")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "amount", "is_successful", "created_at")
    list_filter = ("is_successful", "course", "created_at")
    search_fields = ("user__username", "course__title")