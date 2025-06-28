from django.core.mail import EmailMessage
from authentication.models import UserProfile
from utils import generate_model_pdf
from django.utils import timezone
from administration.models import Heir, Asset, Executor, SpecialAccount, ConfidentialInfo, PostDeathInstruction, AudioInstruction
from django.conf import settings

def get_model_data(user_profile):
    return {
        "UserProfile": [{
            "Full Name": user_profile.full_name,
            "Gender": user_profile.gender,
            "DOB": user_profile.date_of_birth,
            "Phone": user_profile.phone_number,
            "Email": user_profile.email,
            "Roles": user_profile.roles,
            "Created": user_profile.created_at
        }],
        "Heirs": list(user_profile.heirs.values("full_name", "relationship", "date_of_birth", "phone_number")),
        "Assets": list(user_profile.assets.values("asset_type", "location", "estimated_value")),
        "Executors": [vars(user_profile.executor)] if hasattr(user_profile, "executor") else [],
        "SpecialAccounts": list(user_profile.special_accounts.values("account_type", "account_name", "account_number")),
        "ConfidentialInfos": list(user_profile.confidential_infos.values("instructions")),
        "PostDeathInstruction": [{"Instructions": user_profile.post_death_instruction.instructions}] if hasattr(user_profile, "post_death_instruction") else [],
        "AudioInstructions": list(user_profile.audio_instructions.values("id")),
    }

def send_user_pdf_email(user_profile):
    models_data = get_model_data(user_profile)
    pdf_file = generate_model_pdf(user_profile.user, models_data)

    email = EmailMessage(
        subject="Your Seduta Profile Summary",
        body="Attached is your profile and related data.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_profile.email]
    )
    email.attach("seduta_summary.pdf", pdf_file.read(), "application/pdf")
    email.send()
