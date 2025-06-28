from core.celery import shared_task
from authentication.models import UserProfile
from .email_tasks import send_user_pdf_email

@shared_task
def send_summary_pdfs():
    admin_profiles = UserProfile.objects.filter(roles="Admin", email__isnull=False)
    for profile in admin_profiles:
        send_user_pdf_email(profile)
