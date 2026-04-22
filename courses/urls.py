from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/buy/', views.buy_course, name='buy_course'),
    path('course/<int:course_id>/payment-success/', views.payment_success, name='payment_success'),
    path('course/<int:course_id>/video/', views.video_detail, name='video_detail'),
    path('course/<int:course_id>/quiz/', views.quiz_view, name='quiz'),
    path('course/<int:course_id>/certificate/', views.certificate_success, name='certificate_success'),
    path('course/<int:course_id>/certificate-pdf/', views.certificate_pdf, name='certificate_pdf'),
    path("dashboard/", views.dashboard, name="dashboard"),
]