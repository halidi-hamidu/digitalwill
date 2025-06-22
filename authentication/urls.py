from django.urls import path
from .import views

app_name = "authentication"

urlpatterns = [
    path('', views.loginview, name="auth"),
    path('registration/', views.registerview, name="registration"),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify-email'),
    path('user/personal-info/',views.personalinformationview, name="personalinformation"),
    path("resend-verification/", views.resend_verification_email, name="resend_verification"),
    path("verify-email/personal-information/changes/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),

]