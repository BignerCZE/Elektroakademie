from django.contrib import admin
from .models import CustomUser, Course, Question, Choice, Payment


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'course')
    list_filter = ('course',)
    search_fields = ('text',)
    inlines = [ChoiceInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_paid', 'passed_quiz')
    search_fields = ('username', 'email')
    list_filter = ('is_paid', 'passed_quiz')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'amount', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'course', 'created_at')
    search_fields = ('user__username', 'course__title')


