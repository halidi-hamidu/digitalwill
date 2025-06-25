from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    # Dashboard
    path('', views.dashboardview, name="dashboard"),

    # Digital Wills
    path('digital-wills', views.digitalwillview, name="digitalwill"),

    # Heir Management
    path('digital-wills/heir/update/<str:heir_id>/', views.digitalwillUpdateHeirview, name="digitalwillupdateheir"),
    path('digital-wills/heir/delete/<str:heir_id>/', views.digitalwillDeleteHeirview, name="digitalwilldeleteteheir"),

    # Special Account Management
    path('digital-wills/special_account/update/<str:special_account_id>/', views.digitalwillUpdateSpecialAccountview, name='digitalwillspecialaccount'),
    path('digital-wills/special_account/verify_update/<str:token>/', views.verify_special_account_update, name='verify_special_account_update'),
    path('digital-wills/special_account/delete/<uuid:special_account_id>/', views.request_delete_special_account, name='deletespecialaccount'),
    path('digital-wills/special_account/delete/confirm/<uuid:token>/', views.confirm_delete_special_account, name='confirm_delete_special_account'),

    # Asset Management
    path('digital-wills/asset/update/<str:asset_id>/', views.digitalwillUpdateAssetview, name="digitalwillupdateasset"),
    path('digital-wills/asset/delete/<str:asset_id>/', views.digitalwillDeleteAssetview, name="digitalwilldeleteteasset"),

    # Email Verification
    path('verify-heir/<str:token>/', views.verify_heir_view, name="verify_heir"),
    path('verify-asset/<str:token>/', views.verify_asset_view, name="verify_asset"),
    path('resend-asset-verification/', views.resend_asset_verification_email, name="resend_asset_verification"),
    path('verify-special-account/<str:token>/', views.verify_special_account, name="verify_special_account"),
    path('resend-special-account-verification/', views.resend_special_account_verification, name="resend_special_account_verification"),
    path('verify-confidential-info/<str:token>/', views.verify_confidential_info, name="verify_confidential_info"),
    path('resend-confidential-info-verification/', views.resend_confidential_info_verification, name="resend_confidential_info_verification"),
    path('verify-executor/<str:token>/', views.verify_executor, name="verify_executor"),
    path('verify-instruction/<str:token>/', views.verify_instruction, name="verify_instruction"),
    path('verify-audio/<str:token>/', views.verify_audio, name="verify_audio"),
    path('verify-asset-update/<str:token>/', views.verify_asset_update, name="verify_asset_update"),
    path('verify-asset-delete/<str:token>/', views.verify_asset_delete, name="verify_asset_delete"),

    # Confidential Info Management
    path('confidential-info/update/<uuid:id>/', views.update_confidential_info, name='update_confidential_info'),
    path('confirm-update/<uidb64>/<token>/', views.confirm_update_confidential_info, name='confirm_update_confidential_info'),
    path('confidential-info/delete/request/<uuid:id>/', views.request_delete_confidential_info, name='request_delete_confidential_info'),
    path('confidential-info/delete/confirm/<uidb64>/<token>/', views.confirm_delete_confidential_info, name='confirm_delete_confidential_info'),

    # Executor Management
    path('executor/update/request/<uuid:id>/', views.request_update_executor, name='request_update_executor'),
    path('executor/update/confirm/<uidb64>/<token>/', views.confirm_update_executor, name='confirm_update_executor'),
    path('executor/delete/request/<uuid:id>/', views.request_delete_executor, name='request_delete_executor'),
    path('executor/delete/confirm/<uidb64>/<token>/', views.confirm_delete_executor, name='confirm_delete_executor'),

    # Post-Death Instructions
    path('post-death/update/request/<uuid:id>/', views.request_update_post_death, name='request_update_post_death'),
    path('post-death/update/confirm/<uidb64>/<token>/', views.confirm_update_post_death, name='confirm_update_post_death'),
    path('post-death/delete/request/<uuid:id>/', views.request_delete_post_death_instruction, name='request_delete_post_death_instruction'),
    path('post-death/delete/confirm/<uidb64>/<token>/', views.confirm_delete_post_death_instruction, name='confirm_delete_post_death_instruction'),

    # Audio Instructions
    path('audio/update/request/<uuid:id>/', views.request_update_audio_instruction, name='request_update_audio_instruction'),
    path('audio/update/confirm/<uidb64>/<token>/', views.confirm_update_audio_instruction, name='confirm_update_audio_instruction'),
    path('audio/delete/request/<uuid:id>/', views.request_delete_audio_instruction, name='request_delete_audio_instruction'),
    path('audio/delete/confirm/<uidb64>/<token>/', views.confirm_delete_audio_instruction, name='confirm_delete_audio_instruction'),

    path('beneficiary/', views.beneficiaryview, name="beneficiary"),
]
