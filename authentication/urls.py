from django.urls import path
from .import views

app_name = "authentication"

urlpatterns = [
    path('', views.loginview, name="auth"),
    path('registration/', views.registerview, name="registration"),
    path('logout/', views.logoutview, name="logout"),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify-email'),
    path('user/personal-info/',views.personalinformationview, name="personalinformation"),
    path("resend-verification/", views.resend_verification_email, name="resend_verification"),
    path("verify-email/personal-information/changes/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),
    path("account-settings/", views.accountsettingview, name="accountsetting"),
    path("account-settings/delete/<str:user_id>/", views.deleteuseraccountview, name="deleteuseraccount"),
    path("account-settings/update/<str:user_id>/", views.updateuseraccountview, name="updateuseraccount"),
]