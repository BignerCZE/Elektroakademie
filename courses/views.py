import random
from datetime import date
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.forms import formset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from .forms import BillingForm, ParticipantForm
from .models import (
    Choice,
    Course,
    Order,
    OrderParticipant,
    Payment,
    Question,
    QuizAttempt,
    QuizAttemptQuestion,
)

User = get_user_model()


COURSE_PRICES = {
    "4": 990,
    "6": 2990,
    "7": 3490,
}


def get_dashboard_context(request, active_course=None):
    purchased_courses = Course.objects.all()

    if active_course is None:
        active_course = purchased_courses.first()

    has_paid = (
        getattr(request.user, "is_paid", False)
        if request.user.is_authenticated
        else False
    )

    return {
        "purchased_courses": purchased_courses,
        "active_course": active_course,
        "course_for_payment": active_course,
        "has_paid": has_paid,
    }


def index(request):
    courses = Course.objects.all()
    return render(request, "courses/index.html", {"courses": courses})


def landing(request):
    return render(request, "courses/landing.html")


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    context = {
        "course": course,
    }

    if request.user.is_authenticated:
        context.update(
            get_dashboard_context(
                request,
                active_course=course,
            )
        )

    return render(
        request,
        "courses/course_detail.html",
        context,
    )


def register(request):
    ParticipantFormSet = formset_factory(
        ParticipantForm,
        extra=1,
        min_num=1,
        validate_min=True,
    )

    if request.method == "POST":
        participant_formset = ParticipantFormSet(
            request.POST,
            prefix="participants",
        )
        billing_form = BillingForm(request.POST)
        selected_course = request.POST.get("selected_course")

        if (
            selected_course in COURSE_PRICES
            and participant_formset.is_valid()
            and billing_form.is_valid()
        ):
            participants = [
                form.cleaned_data
                for form in participant_formset
                if form.cleaned_data
            ]

            participant_count = len(participants)
            total_price = (
                COURSE_PRICES[selected_course]
                * participant_count
            )

            order = Order.objects.create(
                course_type=selected_course,
                total_price=total_price,
                status="pending_payment",
                ico=billing_form.cleaned_data.get("ico", ""),
                dic=billing_form.cleaned_data.get("dic", ""),
                company_name=billing_form.cleaned_data["company_name"],
                street=billing_form.cleaned_data["street"],
                city=billing_form.cleaned_data["city"],
                zip_code=billing_form.cleaned_data["zip_code"],
                country=billing_form.cleaned_data["country"],
                note=billing_form.cleaned_data.get("note", ""),
            )

            for participant in participants:
                OrderParticipant.objects.create(
                    order=order,
                    first_name=participant["first_name"],
                    last_name=participant["last_name"],
                    email=participant["email"],
                )

            first_participant = participants[0]
            email = first_participant["email"]

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_participant["first_name"],
                    "last_name": first_participant["last_name"],
                    "is_active": True,
                },
            )

            if created:
                user.set_unusable_password()
                user.save()

            return redirect(
                "order_payment_simulation",
                order_id=order.id,
            )

    else:
        participant_formset = ParticipantFormSet(
            prefix="participants",
        )
        billing_form = BillingForm()

    return render(
        request,
        "registration/register.html",
        {
            "participant_formset": participant_formset,
            "billing_form": billing_form,
        },
    )


def order_payment_simulation(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
    )

    return render(
        request,
        "registration/payment_simulation.html",
        {
            "order": order,
        },
    )


def order_payment_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
    )

    if order.status != "paid":
        order.status = "paid"
        order.paid_at = timezone.now()
        order.save()

    return render(
        request,
        "registration/order_payment_success.html",
        {
            "order": order,
        },
    )


def password_setup_sent(request):
    return render(
        request,
        "registration/password_setup_sent.html",
    )


@login_required
def profile(request):
    context = get_dashboard_context(request)

    return render(
        request,
        "courses/profile.html",
        context,
    )


@login_required
def buy_course(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if request.method == "POST":
        Payment.objects.create(
            user=request.user,
            course=course,
            amount=999.00,
            is_successful=True,
        )

        request.user.is_paid = True
        request.user.save()

        return redirect(
            "payment_success",
            course_id=course.id,
        )

    context = {
        "course": course,
    }
    context.update(
        get_dashboard_context(
            request,
            active_course=course,
        )
    )

    return render(
        request,
        "courses/buy_course.html",
        context,
    )


@login_required
def payment_success(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    context = {
        "course": course,
    }
    context.update(
        get_dashboard_context(
            request,
            active_course=course,
        )
    )

    return render(
        request,
        "courses/payment_success.html",
        context,
    )


@login_required
def video_detail(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if not request.user.is_paid:
        return redirect(
            "buy_course",
            course_id=course.id,
        )

    context = {
        "course": course,
    }
    context.update(
        get_dashboard_context(
            request,
            active_course=course,
        )
    )

    return render(
        request,
        "courses/video_detail.html",
        context,
    )


@login_required
def quiz_dashboard(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if not request.user.is_paid:
        return redirect(
            "buy_course",
            course_id=course.id,
        )

    active_attempt = (
        QuizAttempt.objects
        .filter(
            user=request.user,
            course=course,
            status=QuizAttempt.STATUS_IN_PROGRESS,
        )
        .first()
    )

    past_attempts = (
        QuizAttempt.objects
        .filter(
            user=request.user,
            course=course,
            status=QuizAttempt.STATUS_SUBMITTED,
        )
        .order_by(
            "-submitted_at",
            "-started_at",
        )
    )

    context = {
        "course": course,
        "active_attempt": active_attempt,
        "past_attempts": past_attempts,
    }
    context.update(
        get_dashboard_context(
            request,
            active_course=course,
        )
    )

    return render(
        request,
        "courses/quiz_dashboard.html",
        context,
    )


@login_required
def quiz_start(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if not request.user.is_paid:
        return redirect(
            "buy_course",
            course_id=course.id,
        )

    active_attempt = (
        QuizAttempt.objects
        .filter(
            user=request.user,
            course=course,
            status=QuizAttempt.STATUS_IN_PROGRESS,
        )
        .first()
    )

    if active_attempt:
        return redirect(
            "quiz_question",
            attempt_id=active_attempt.id,
            order=1,
        )

    category_counts = getattr(
        settings,
        "QUIZ_CATEGORY_COUNTS",
        [
            ("obecne", 8),
            ("zdravotni", 2),
        ],
    )

    selected_questions = []

    for category_slug, count in category_counts:
        questions = list(
            Question.objects.filter(
                course=course,
                category__slug=category_slug,
            )
        )

        if len(questions) < count:
            return HttpResponse(
                f"V kategorii '{category_slug}' není dostatek otázek. "
                f"Požadováno: {count}, dostupné: {len(questions)}.",
                status=400,
            )

        selected_questions.extend(
            random.sample(
                questions,
                count,
            )
        )

    current_max_attempt_number = (
        QuizAttempt.objects
        .filter(user=request.user)
        .aggregate(
            max_number=Max("attempt_number")
        )
        .get("max_number")
        or 0
    )

    next_attempt_number = (
        current_max_attempt_number + 1
    )

    attempt = QuizAttempt.objects.create(
        user=request.user,
        course=course,
        total_questions=len(selected_questions),
        attempt_number=next_attempt_number,
    )

    for index, question in enumerate(
        selected_questions,
        start=1,
    ):
        QuizAttemptQuestion.objects.create(
            attempt=attempt,
            question=question,
            order=index,
        )

    return redirect(
        "quiz_question",
        attempt_id=attempt.id,
        order=1,
    )


@login_required
def quiz_question(request, attempt_id, order):
    attempt = get_object_or_404(
        QuizAttempt,
        id=attempt_id,
        user=request.user,
    )

    if attempt.status == QuizAttempt.STATUS_SUBMITTED:
        return redirect(
            "quiz_attempt_detail",
            attempt_id=attempt.id,
            order=1,
        )

    total_questions = (
        attempt.attempt_questions.count()
    )

    attempt_question = get_object_or_404(
        QuizAttemptQuestion,
        attempt=attempt,
        order=order,
    )

    if request.method == "POST":
        choice_id = request.POST.get("choice")

        if choice_id:
            choice = (
                Choice.objects
                .filter(
                    id=choice_id,
                    question=attempt_question.question,
                )
                .first()
            )

            if choice:
                attempt_question.selected_choice = choice
                attempt_question.save(
                    update_fields=["selected_choice"]
                )

        if "leave_test" in request.POST:
            return redirect(
                "quiz",
                course_id=attempt.course.id,
            )

        if "previous" in request.POST:
            previous_order = max(
                order - 1,
                1,
            )

            return redirect(
                "quiz_question",
                attempt_id=attempt.id,
                order=previous_order,
            )

        if "next" in request.POST:
            if order == total_questions:
                return redirect(
                    "quiz_submit",
                    attempt_id=attempt.id,
                )

            return redirect(
                "quiz_question",
                attempt_id=attempt.id,
                order=order + 1,
            )

        if "submit_test" in request.POST:
            return redirect(
                "quiz_submit",
                attempt_id=attempt.id,
            )

        return redirect(
            "quiz_question",
            attempt_id=attempt.id,
            order=order,
        )

    choices = []

    for choice in (
        attempt_question.question
        .choice_set
        .all()
    ):
        choices.append({
            "id": choice.id,
            "text": choice.text,
            "checked": (
                "checked"
                if choice.id
                == attempt_question.selected_choice_id
                else ""
            ),
        })

    answered_question_orders = set(
        attempt.attempt_questions
        .filter(selected_choice__isnull=False)
        .values_list(
            "order",
            flat=True,
        )
    )

    unanswered_questions = [
        number
        for number in range(
            1,
            total_questions + 1,
        )
        if number not in answered_question_orders
    ]

    unanswered_count = len(
        unanswered_questions
    )

    question_numbers = []

    for number in range(
        1,
        total_questions + 1,
    ):
        question_numbers.append({
            "number": number,
            "is_current": number == order,
            "is_answered": (
                number in answered_question_orders
            ),
        })

    context = {
        "attempt": attempt,
        "attempt_question": attempt_question,
        "course": attempt.course,
        "order": order,
        "total_questions": total_questions,
        "question_numbers": question_numbers,
        "unanswered_count": unanswered_count,
        "unanswered_questions": unanswered_questions,
        "choices": choices,
        "is_first": order == 1,
        "is_last": order == total_questions,
    }

    context.update(
        get_dashboard_context(
            request,
            active_course=attempt.course,
        )
    )

    return render(
        request,
        "courses/quiz_question.html",
        context,
    )


@login_required
def quiz_attempt(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        id=attempt_id,
        user=request.user,
    )

    if attempt.status == QuizAttempt.STATUS_SUBMITTED:
        return redirect(
            "quiz_attempt_detail",
            attempt_id=attempt.id,
            order=1,
        )

    if request.method == "POST":
        attempt_questions = (
            attempt.attempt_questions
            .select_related("question")
        )

        for attempt_question in attempt_questions:
            choice_id = request.POST.get(
                f"question_{attempt_question.id}"
            )

            if choice_id:
                choice = (
                    Choice.objects
                    .filter(
                        id=choice_id,
                        question=attempt_question.question,
                    )
                    .first()
                )

                if choice:
                    attempt_question.selected_choice = choice
                    attempt_question.save(
                        update_fields=["selected_choice"]
                    )

        return redirect(
            "quiz_attempt",
            attempt_id=attempt.id,
        )

    context = {
        "attempt": attempt,
        "course": attempt.course,
    }
    context.update(
        get_dashboard_context(
            request,
            active_course=attempt.course,
        )
    )

    return render(
        request,
        "courses/quiz_attempt.html",
        context,
    )


@login_required
def quiz_submit(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        id=attempt_id,
        user=request.user,
        status=QuizAttempt.STATUS_IN_PROGRESS,
    )

    unanswered_question = (
        attempt.attempt_questions
        .filter(selected_choice__isnull=True)
        .order_by("order")
        .first()
    )

    if unanswered_question:
        return redirect(
            "quiz_question",
            attempt_id=attempt.id,
            order=unanswered_question.order,
        )

    total_questions = (
        attempt.attempt_questions.count()
    )

    correct_answers = (
        attempt.attempt_questions
        .filter(selected_choice__is_correct=True)
        .count()
    )

    score_percent = 0

    if total_questions:
        score_percent = round(
            (
                correct_answers
                / total_questions
            )
            * 100,
            2,
        )

    pass_percentage = getattr(
        settings,
        "QUIZ_PASS_PERCENTAGE",
        70,
    )

    passed = (
        score_percent >= pass_percentage
    )

    attempt.total_questions = total_questions
    attempt.correct_answers = correct_answers
    attempt.score_percent = score_percent
    attempt.passed = passed
    attempt.status = QuizAttempt.STATUS_SUBMITTED
    attempt.submitted_at = timezone.now()

    attempt.save(
        update_fields=[
            "total_questions",
            "correct_answers",
            "score_percent",
            "passed",
            "status",
            "submitted_at",
        ]
    )

    if passed:
        request.user.passed_quiz = True
        request.user.save(
            update_fields=["passed_quiz"]
        )

    return redirect(
        "quiz_attempt_detail",
        attempt_id=attempt.id,
        order=1,
    )


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("course"),
        id=attempt_id,
        user=request.user,
        status=QuizAttempt.STATUS_SUBMITTED,
    )

    return redirect(
        "quiz_attempt_detail",
        attempt_id=attempt.id,
        order=1,
    )


@login_required
def quiz_attempt_detail(
    request,
    attempt_id,
    order,
):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("course"),
        id=attempt_id,
        user=request.user,
        status=QuizAttempt.STATUS_SUBMITTED,
    )

    attempt_questions = (
        QuizAttemptQuestion.objects
        .filter(attempt=attempt)
        .select_related(
            "question",
            "selected_choice",
        )
        .prefetch_related(
            "question__choice_set"
        )
        .order_by("order")
    )

    total_questions = (
        attempt_questions.count()
    )

    attempt_question = get_object_or_404(
        attempt_questions,
        order=order,
    )

    question_numbers = []

    for item in attempt_questions:
        selected_choice = item.selected_choice

        is_correct = bool(
            selected_choice
            and selected_choice.is_correct
        )

        question_numbers.append({
            "order": item.order,
            "is_current": item.order == order,
            "is_correct": is_correct,
        })

    context = {
        "attempt": attempt,
        "attempt_question": attempt_question,
        "question_numbers": question_numbers,
        "order": order,
        "total_questions": total_questions,
        "is_first": order == 1,
        "is_last": order == total_questions,
        "came_from_result": (
            request.GET.get("from")
            == "result"
        ),
    }

    context.update(
        get_dashboard_context(
            request,
            active_course=attempt.course,
        )
    )

    return render(
        request,
        "courses/quiz_attempt_detail.html",
        context,
    )


@login_required
def certificate_success(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if not request.user.is_paid:
        return redirect(
            "buy_course",
            course_id=course.id,
        )

    if not request.user.passed_quiz:
        return redirect(
            "quiz",
            course_id=course.id,
        )

    context = {
        "course": course,
        "completion_date": date.today(),
    }

    context.update(
        get_dashboard_context(
            request,
            active_course=course,
        )
    )

    return render(
        request,
        "courses/certificate_success.html",
        context,
    )


@login_required
def certificate_pdf(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
    )

    if not request.user.is_paid:
        return redirect(
            "buy_course",
            course_id=course.id,
        )

    if not request.user.passed_quiz:
        return redirect(
            "quiz",
            course_id=course.id,
        )

    template = get_template(
        "courses/certificate_pdf.html"
    )

    html = template.render({
        "user": request.user,
        "course": course,
        "completion_date": date.today(),
    })

    result = BytesIO()

    pdf = pisa.CreatePDF(
        src=html,
        dest=result,
    )

    if pdf.err:
        return HttpResponse(
            "Chyba při generování PDF certifikátu",
            status=500,
        )

    response = HttpResponse(
        result.getvalue(),
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'inline; filename="certificate.pdf"'
    )

    return response


@login_required
def dashboard(request):
    context = get_dashboard_context(request)

    return render(
        request,
        "courses/dashboard.html",
        context,
    )


def course_selector(request):
    return render(
        request,
        "courses/course_selector.html",
    )


def terms_and_conditions(request):
    return render(
        request,
        "courses/terms_and_conditions.html",
    )


def privacy_policy(request):
    return render(
        request,
        "courses/privacy_policy.html",
    )