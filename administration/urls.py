from django.urls import path
from .import views

app_name = "administration"

urlpatterns = [
    path('',views.dashboardview, name="dashboard"),
    path('digital-wills',views.digitalwillview, name="digitalwill"),
    path('digital-wills/heir/update/<str:heir_id>/',views.digitalwillUpdateHeirview, name="digitalwillupdateheir"),
    path('digital-wills/heir/delete/<str:heir_id>/',views.digitalwillDeleteHeirview, name="digitalwilldeleteteheir"),

    # email verification urls
    path("verify-heir/<str:token>/", views.verify_heir_view, name="verify_heir"),
    path("verify-asset/<str:token>/", views.verify_asset_view, name="verify_asset"),
    path("resend-asset-verification/", views.resend_asset_verification_email, name="resend_asset_verification"),
    path("verify-special-account/<str:token>/", views.verify_special_account, name="verify_special_account"),
    path(
    "resend-special-account-verification/",
    views.resend_special_account_verification,
    name="resend_special_account_verification"
    ),
    path("verify-confidential-info/<str:token>/", views.verify_confidential_info, name="verify_confidential_info"),
    path("resend-confidential-info-verification/", views.resend_confidential_info_verification, name="resend_confidential_info_verification"),
    path("verify-executor/<str:token>/", views.verify_executor, name="verify_executor"),
    path("verify-instruction/<str:token>/", views.verify_instruction, name="verify_instruction"),
    path("verify-audio/<str:token>/", views.verify_audio, name="verify_audio"),

    path('digital-wills/asset/update/<str:asset_id>/',views.digitalwillUpdateAssetview, name="digitalwillupdateasset"),
    path('digital-wills/asset/delete/<str:asset_id>/',views.digitalwillDeleteAssetview, name="digitalwilldeleteteasset"),
]