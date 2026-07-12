from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    # domovská stránka
    path("", views.index, name="index"),

    # kurzy
    path("kurzy/", views.index, name="courses"),
    path("kurz/<int:course_id>/", views.course_detail, name="course_detail"),

    # registrace (bez hesla)
    path("registrace/", views.register, name="register"),
    path("registrace/odeslano/", views.password_setup_sent, name="password_setup_sent"),

    # nastavení hesla přes e-mail
    path(
        "heslo/nastavit/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_setup_confirm.html",
            success_url="/heslo/hotovo/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "heslo/hotovo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_setup_complete.html",
        ),
        name="password_reset_complete",
    ),

    # přihlášení / odhlášení
    path(
        "prihlaseni/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),
    path(
        "odhlaseni/",
        auth_views.LogoutView.as_view(next_page="index"),
        name="logout",
    ),

    # uživatelská sekce
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profil/", views.profile, name="profile"),

    # nákup
    path("kurz/<int:course_id>/koupit/", views.buy_course, name="buy_course"),
    path("kurz/<int:course_id>/zaplaceno/", views.payment_success, name="payment_success"),
    path("vyber-kurzu/", views.course_selector, name="course_selector"),

    # obsah kurzu
    path("kurz/<int:course_id>/video/", views.video_detail, name="video_detail"),
    path("kurz/<int:course_id>/test/", views.quiz_dashboard, name="quiz"),
    path("kurz/<int:course_id>/test/spustit/", views.quiz_start, name="quiz_start"),
    path("test/<int:attempt_id>/", views.quiz_attempt, name="quiz_attempt"),
    path("test/<int:attempt_id>/odeslat/", views.quiz_submit, name="quiz_submit"),
    path("test/<int:attempt_id>/vysledek/", views.quiz_result, name="quiz_result"),

    path("test/<int:attempt_id>/otazka/<int:order>/", views.quiz_question, name="quiz_question"),
    # certifikát
    path("kurz/<int:course_id>/certifikat/", views.certificate_success, name="certificate_success"),
    path("kurz/<int:course_id>/certifikat/pdf/", views.certificate_pdf, name="certificate_pdf"),

    path("platba/<int:order_id>/", views.order_payment_simulation, name="order_payment_simulation"),
    path("platba/<int:order_id>/dokonceno/", views.order_payment_success, name="order_payment_success"),
    
    path(
        "aktivace/<uuid:token>/",
        views.participant_activation,
        name="participant_activation",
    ),

    path("obchodni-podminky/", views.terms_and_conditions, name="terms_and_conditions"),
    path("zasady-ochrany-osobnich-udaju/", views.privacy_policy, name="privacy_policy"),

    path(
        "test/<int:attempt_id>/nahled/<int:order>/",
        views.quiz_attempt_detail,
        name="quiz_attempt_detail",
    ),

    path(
        "api/ares/<str:ico>/",
        views.ares_company_detail,
        name="ares_company_detail",
    ),
]