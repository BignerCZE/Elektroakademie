import random
from datetime import date
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from xhtml2pdf import pisa
from django.forms import formset_factory

from .forms import BillingForm, ParticipantForm
from .models import Choice, Course, Payment, Question


def get_dashboard_context(request, active_course=None):
    purchased_courses = Course.objects.all()

    if active_course is None:
        active_course = purchased_courses.first()

    has_paid = getattr(request.user, "is_paid", False) if request.user.is_authenticated else False

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

    context = {"course": course}

    if request.user.is_authenticated:
        context.update(get_dashboard_context(request, active_course=course))

    return render(request, "courses/course_detail.html", context)


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

        if participant_formset.is_valid() and billing_form.is_valid():
            first_participant = participant_formset.cleaned_data[0]

            email = first_participant["email"]

            user = CustomUser.objects.create(
                username=email,
                email=email,
                first_name=first_participant["first_name"],
                last_name=first_participant["last_name"],
                is_active=True,
            )

            user.set_unusable_password()
            user.save()

            current_site = get_current_site(request)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            password_setup_url = request.build_absolute_uri(
                reverse(
                    "password_reset_confirm",
                    kwargs={
                        "uidb64": uid,
                        "token": token,
                    },
                )
            )

            subject = "Nastavení hesla | Elektroakademie"

            message = render_to_string(
                "registration/password_setup_email.txt",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "password_setup_url": password_setup_url,
                },
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=False,
            )

            return redirect("password_setup_sent")

    else:
        participant_formset = ParticipantFormSet(prefix="participants")
        billing_form = BillingForm()

    return render(
        request,
        "registration/register.html",
        {
            "participant_formset": participant_formset,
            "billing_form": billing_form,
        },
    )


def password_setup_sent(request):
    return render(request, "registration/password_setup_sent.html")


@login_required
def profile(request):
    context = get_dashboard_context(request)
    return render(request, "courses/profile.html", context)


@login_required
def buy_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        Payment.objects.create(
            user=request.user,
            course=course,
            amount=999.00,
            is_successful=True,
        )
        request.user.is_paid = True
        request.user.save()
        return redirect("payment_success", course_id=course.id)

    context = {"course": course}
    context.update(get_dashboard_context(request, active_course=course))
    return render(request, "courses/buy_course.html", context)


@login_required
def payment_success(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    context = {"course": course}
    context.update(get_dashboard_context(request, active_course=course))
    return render(request, "courses/payment_success.html", context)


@login_required
def video_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_paid:
        return redirect("buy_course", course_id=course.id)

    context = {"course": course}
    context.update(get_dashboard_context(request, active_course=course))
    return render(request, "courses/video_detail.html", context)


@login_required
def quiz_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_paid:
        return redirect("buy_course", course_id=course.id)

    all_questions = list(Question.objects.filter(course=course))
    question_count = getattr(settings, "QUIZ_QUESTION_COUNT", 3)

    if request.method == "POST":
        selected_question_ids = request.session.get("selected_question_ids", [])
        questions = Question.objects.filter(id__in=selected_question_ids, course=course)

        total_questions = questions.count()
        correct_answers = 0

        for question in questions:
            selected_choice_id = request.POST.get(str(question.id))

            if selected_choice_id:
                try:
                    choice = Choice.objects.get(id=selected_choice_id, question=question)
                    if choice.is_correct:
                        correct_answers += 1
                except Choice.DoesNotExist:
                    pass

        score_percent = 0

        if total_questions > 0:
            score_percent = (correct_answers / total_questions) * 100

        pass_percentage = getattr(settings, "QUIZ_PASS_PERCENTAGE", 70)
        passed = score_percent >= pass_percentage

        if passed:
            request.user.passed_quiz = True
            request.user.save()

        context = {
            "course": course,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "score_percent": score_percent,
            "passed": passed,
            "pass_percentage": pass_percentage,
        }

        context.update(get_dashboard_context(request, active_course=course))
        return render(request, "courses/quiz_result.html", context)

    if len(all_questions) <= question_count:
        selected_questions = all_questions
    else:
        selected_questions = random.sample(all_questions, question_count)

    request.session["selected_question_ids"] = [
        question.id for question in selected_questions
    ]

    context = {
        "course": course,
        "questions": selected_questions,
    }

    context.update(get_dashboard_context(request, active_course=course))
    return render(request, "courses/quiz.html", context)


@login_required
def certificate_success(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_paid:
        return redirect("buy_course", course_id=course.id)

    if not request.user.passed_quiz:
        return redirect("quiz", course_id=course.id)

    context = {
        "course": course,
        "completion_date": date.today(),
    }

    context.update(get_dashboard_context(request, active_course=course))
    return render(request, "courses/certificate_success.html", context)


@login_required
def certificate_pdf(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_paid:
        return redirect("buy_course", course_id=course.id)

    if not request.user.passed_quiz:
        return redirect("quiz", course_id=course.id)

    template = get_template("courses/certificate_pdf.html")

    html = template.render(
        {
            "user": request.user,
            "course": course,
            "completion_date": date.today(),
        }
    )

    result = BytesIO()
    pdf = pisa.CreatePDF(src=html, dest=result)

    if pdf.err:
        return HttpResponse("Chyba při generování PDF certifikátu", status=500)

    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="certificate.pdf"'
    return response


@login_required
def dashboard(request):
    context = get_dashboard_context(request)
    return render(request, "courses/dashboard.html", context)

    
def course_selector(request):
    return render(request, "courses/course_selector.html")