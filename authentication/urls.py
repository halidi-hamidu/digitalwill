from django.urls import path
from .import views
from django.contrib.auth import views as auth_views
from .views import CustomPasswordResetView

app_name = "authentication"

urlpatterns = [
    path('', views.loginview, name="auth"),
    path('registration/', views.registerview, name="registration"),
    path("authenticationverify-email/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),
    path('logout/', views.logoutview, name="logout"),
    path('user/personal-info/',views.personalinformationview, name="personalinformation"),
    path("verify-email/<token>/", views.verify_email, name="verify_email"),

    path("account-settings/", views.accountsettingview, name="accountsetting"),
    path("account-settings/delete/user/<str:user_id>/", views.deleteuseraccountview, name="deleteuseraccount"),
    path("account-settings/update/<str:user_id>/", views.updateuseraccountview, name="updateuseraccount"),

    # Password reset
    # Use the custom PasswordResetView here
    path('password_reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),
]

password_urlpatterns = [
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

urlpatterns += password_urlpatterns