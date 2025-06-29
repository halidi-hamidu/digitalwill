from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import *
from django.db.models import Q
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.core.mail import EmailMessage
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
import uuid
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Image as RLImage
from reportlab.lib.utils import ImageReader
import os
from utils import *
import uuid
from django.core.signing import Signer
from django.core.files.base import ContentFile
from django.utils import timezone
import io
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.http import HttpResponse
from .models import ConfidentialInfo
from .forms import ConfidentialInfoForm
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.files import File
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from weasyprint import HTML
from django.db.models import Sum, Count
import json
from datetime import date

from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six
import weasyprint  # or use xhtml2pdf / reportlab
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from tokens import *
from django.core.files.storage import default_storage
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required

User = get_user_model()
class UpdateEmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

email_verification_token = UpdateEmailVerificationTokenGenerator()

signer = TimestampSigner()
TOKEN_EXPIRY_SECONDS = 86400  # 1 day

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_heir_view(request, token):
    try:
        # Validate token (max_age: 1 hour)
        signer.unsign(token, max_age=3600)

        # Check for a valid pending heir record
        pending = PendingHeirVerification.objects.filter(token=token).first()
        if not pending:
            messages.error(request, "Invalid or already used verification link.")
            return redirect("administration:digitalwill")

        # Create verified heir record
        heir = Heir.objects.create(
            testator=pending.testator,
            full_name=pending.full_name,
            relationship=pending.relationship,
            date_of_birth=pending.date_of_birth,
            phone_number=pending.phone_number,
        )

        # Generate PDF summary
        pdf_buffer = generate_heir_verification_pdf(heir)

        # Send confirmation to the heir (via testator's email)
        heir_email = EmailMessage(
            subject="Heir Verification Successful — Seduta Will",
            body=(
                f"Dear {heir.full_name},\n\n"
                "You have been successfully verified and added as an official heir in the Seduta Will system.\n"
                "Attached is a summary of your registered details.\n\n"
                "If this was not authorized by you, please contact our support team immediately.\n\n"
                "— Seduta Will"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[pending.testator.email],
        )
        heir_email.attach("heir_verification.pdf", pdf_buffer.getvalue(), "application/pdf")
        heir_email.send(fail_silently=False)

        # Notify all admins
        admin_emails = list(
            User.objects.filter(user_userprofile__roles="Admin")
                        .values_list("email", flat=True)
        )
        if admin_emails:
            admin_email = EmailMessage(
                subject=f"New Verified Heir: {heir.full_name}",
                body=(
                    f"Dear Admin,\n\n"
                    f"The following heir has been verified and added to the system under testator {heir.testator.get_full_name()}:\n\n"
                    f"Name: {heir.full_name}\n"
                    f"Relationship: {heir.relationship}\n"
                    f"Phone: {heir.phone_number}\n"
                    f"DOB: {heir.date_of_birth.strftime('%d %B %Y') if heir.date_of_birth else 'N/A'}\n\n"
                    "Attached is a summary in PDF format.\n\n"
                    "— Seduta Will System"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails,
            )
            admin_email.attach("verified_heir_summary.pdf", pdf_buffer.getvalue(), "application/pdf")
            admin_email.send(fail_silently=False)

        # Delete token entry
        pending.delete()

        messages.success(request, f"Heir '{heir.full_name}' successfully verified and added.")
        return redirect("administration:digitalwill")

    except SignatureExpired:
        messages.error(request, "Verification link has expired.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")

    return redirect("administration:digitalwill")


def asset_summary_chart(request):
    user = request.user.userprofile

    # Group asset values by asset_type
    asset_data = (
        Asset.objects.filter(testator=user)
        .values('asset_type')
        .annotate(total_value=Sum('estimated_value'))
        .order_by('-total_value')
    )

    labels = [item['asset_type'] or "Unknown" for item in asset_data]
    data = [float(item['total_value']) for item in asset_data]

    context = {
        'labels': labels,
        'data': data,
    }

    return render(request, 'administration/charts/asset_chart.html', context)

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_asset_view(request, token):
    try:
        # Validate token with 1-day expiry
        signer.unsign(token, max_age=86400)

        # Get pending asset data from session
        pending = request.session.get("pending_asset")
        if not pending:
            messages.error(request, "No pending asset data found.")
            return redirect("administration:digitalwill")

        # Retrieve testator profile
        testator = get_object_or_404(UserProfile, id=pending["testator_id"])

        # Create the asset
        asset = Asset.objects.create(
            testator=testator,
            asset_type=pending["asset_type"],
            location=pending["location"],
            estimated_value=pending["estimated_value"],
            instruction=pending["instruction"],
        )

        # Assign heirs to the asset
        heirs = Heir.objects.filter(id__in=pending["assigned_to"])
        asset.assigned_to.set(heirs)
        asset.save()

        # Clear session and confirm
        del request.session["pending_asset"]
        messages.success(request, "Asset successfully verified and added.")
        return redirect("administration:digitalwill")

    except SignatureExpired:
        messages.error(request, "Verification link has expired.")
    except BadSignature:
        messages.error(request, "Invalid verification token.")

    return redirect("administration:digitalwill")

@cache_control(no_cache=True, privacy=True, must_revalidate=True, no_store=True)
@login_required
def resend_asset_verification_email(request):
    # Retrieve the latest pending asset for the user from DB
    pending = PendingAssetVerification.objects.filter(testator__user=request.user).order_by('-created_at').first()

    if not pending:
        messages.error(request, "No pending asset found to resend.")
        return redirect("administration:digitalwill")

    testator = pending.testator

    # Generate a new token and update the model
    new_token = signer.sign(str(uuid.uuid4()))
    pending.token = new_token
    pending.save()

    verification_url = request.build_absolute_uri(
        reverse("administration:verify_asset", kwargs={"token": new_token})
    )

    # Generate asset PDF from the stored asset_data JSON
    pdf_buffer = generate_asset_pdf(pending.asset_data, testator.full_name)

    # Send the verification email
    email = EmailMessage(
        subject="Verify Asset Addition (Resent)",
        body=f"Please confirm this asset by clicking the link below:\n{verification_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    email.attach("asset_details.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.info(request, "Verification email resent. Please check your inbox.")
    return redirect("administration:digitalwill")


# @cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
# @login_required
# def resend_asset_verification_email(request):
#     # Retrieve pending asset from session
#     pending = request.session.get("pending_asset")
#     if not pending:
#         messages.error(request, "No pending asset found to resend.")
#         return redirect("administration:digitalwill")

#     testator = get_object_or_404(UserProfile, id=pending["testator_id"])

#     # Generate a new token and verification link
#     token = signer.sign(str(uuid.uuid4()))
#     verification_url = request.build_absolute_uri(
#         reverse("administration:verify_asset", kwargs={"token": token})
#     )

#     # Generate asset PDF (image is optional, placeholder for now)
#     image_file = None  # Optional image if available
#     pdf_buffer = generate_asset_pdf(pending, testator.full_name, image_file=image_file)

#     # Send the verification email
#     email = EmailMessage(
#         subject="Verify Asset Addition (Resent)",
#         body=f"Please confirm this asset by clicking the link below:\n{verification_url}",
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to=[request.user.email],
#     )
#     email.attach("asset_details.pdf", pdf_buffer.getvalue(), "application/pdf")
#     email.send()

#     messages.info(request, "Verification email resent. Please check your inbox.")
#     return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_special_account(request, token):
    try:
        # Verify the token with expiry
        signer.unsign(token, max_age=TOKEN_EXPIRY_SECONDS)

        # Retrieve pending special account data from session
        pending = request.session.get("pending_special_account")
        if not pending:
            messages.error(request, "No pending special account found.")
            return redirect("administration:digitalwill")

        # Fetch testator and heir
        testator = get_object_or_404(UserProfile, id=pending["testator_id"])
        heir = get_object_or_404(Heir, id=pending["assigned_to_id"])

        # Create the special account entry
        SpecialAccount.objects.create(
            testator=testator,
            account_type=pending["account_type"],
            account_name=pending["account_name"],
            account_number=pending["account_number"],
            assigned_to=heir,
        )

        # Remove pending data from session
        del request.session["pending_special_account"]
        messages.success(request, "Special account verified and added successfully.")

    except SignatureExpired:
        messages.error(request, "Verification link has expired. Please request a new one.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")

    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def resend_special_account_verification(request):
    # Retrieve pending data from session
    pending = request.session.get("pending_special_account")
    if not pending:
        messages.error(request, "No pending special account to verify.")
        return redirect("administration:digitalwill")

    # Get the testator profile
    userprofile = get_object_or_404(UserProfile, id=pending["testator_id"])

    # Generate a new signed token and verification URL
    token = signer.sign(str(uuid.uuid4()))
    verification_url = request.build_absolute_uri(
        reverse("administration:verify_special_account", kwargs={"token": token})
    )

    # Generate the attached PDF
    pdf_buffer = generate_special_account_pdf(pending, userprofile.full_name)

    # Compose and send the email
    email = EmailMessage(
        subject="Resend: Verify Special Account Addition",
        body=f"""
            Hello {userprofile.full_name},

            You recently requested to add a special account to your digital will.

            Please confirm this by clicking the link below:
            {verification_url}

            If you didn’t request this, you can safely ignore this email.

            Thanks,
            Your Digital Will Team
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    email.attach("special_account.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.success(request, "Verification email resent. Please check your inbox.")
    return redirect("administration:digitalwill")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required
def verify_confidential_info(request, token):
    try:
        pending_id = signer.unsign(token, max_age=TOKEN_EXPIRY_SECONDS)

        pending_update = get_object_or_404(PendingConfidentialInfoUpdate, id=pending_id)

        # Update the linked ConfidentialInfo with pending data
        confidential_info = pending_update.confidential_info
        confidential_info.instructions = pending_update.instructions
        confidential_info.assigned_to.set(pending_update.assigned_to.all())

        if pending_update.uploaded_file:
            # Replace confidential file with pending file
            confidential_info.confidential_file.save(
                pending_update.uploaded_file.name,
                File(pending_update.uploaded_file.file),
                save=False,
            )

        confidential_info.save()

        # Remove the pending update record (and its uploaded_file)
        pending_update.uploaded_file.delete(save=False)
        pending_update.delete()

        messages.success(request, "Confidential information verified and saved.")

    except SignatureExpired:
        messages.error(request, "Verification link has expired.")
    except BadSignature:
        messages.error(request, "Invalid verification token.")
    except Exception as e:
        messages.error(request, f"Error during verification: {str(e)}")

    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def resend_confidential_info_verification(request):
    # Check if session contains pending confidential info
    pending = request.session.get("pending_confidential_info")
    if not pending:
        messages.error(request, "No pending confidential info to resend.")
        return redirect("administration:digitalwill")

    # Get the testator's profile for PDF branding
    userprofile = get_object_or_404(UserProfile, id=pending["testator_id"])

    # Generate a new signed token and verification URL
    token = signer.sign(str(uuid.uuid4()))
    verification_url = request.build_absolute_uri(
        reverse("administration:verify_confidential_info", kwargs={"token": token})
    )

    # Generate a branded PDF summary
    pdf_buffer = generate_confidential_info_pdf(pending, userprofile.full_name)

    # Compose and send the email with PDF attachment
    email = EmailMessage(
        subject="Resend: Verify Confidential Info Submission",
        body=f"""
        Hello {userprofile.full_name},

        You recently submitted confidential information to be added to your digital will.

        To confirm this submission, please click the link below:
        {verification_url}

        If you did not initiate this request, you can safely ignore this email.

        Thank you,  
        Your Digital Will Team
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    email.attach("confidential_info.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.success(request, "Verification email resent. Please check your inbox.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_executor(request, token):
    try:
        # Validate token
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification link.")
        return redirect("administration:digitalwill")

    # Retrieve pending executor data from session
    data = request.session.get("pending_executor")
    if not data:
        messages.error(request, "No executor data found.")
        return redirect("administration:digitalwill")

    # Create executor entry
    testator = get_object_or_404(UserProfile, id=data["testator_id"])
    Executor.objects.create(
        testator=testator,
        full_name=data["full_name"],
        relationship=data["relationship"],
        phone_number=data["phone_number"],
    )

    # Clear session
    request.session.pop("pending_executor", None)
    messages.success(request, "Executor has been successfully added.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_instruction(request, token):
    try:
        # Validate token
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification link.")
        return redirect("administration:digitalwill")

    # Get instruction data from session
    data = request.session.get("pending_instruction")
    if not data:
        messages.error(request, "No instruction data found.")
        return redirect("administration:digitalwill")

    testator = get_object_or_404(UserProfile, id=data["testator_id"])

    # Create or update post-death instructions
    PostDeathInstruction.objects.update_or_create(
        testator=testator,
        defaults={"instructions": data["instructions"]}
    )

    # Clear session
    request.session.pop("pending_instruction", None)
    messages.success(request, "Post-death instructions saved successfully.")
    return redirect("administration:digitalwill")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required
def verify_audio(request, token):
    try:
        # Validate token signature (raises BadSignature if invalid)
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification link.")
        return redirect("administration:digitalwill")

    # Find pending audio upload by token
    try:
        pending_audio = PendingAudioUpload.objects.get(token=token)
    except PendingAudioUpload.DoesNotExist:
        messages.error(request, "No pending audio instruction found.")
        return redirect("administration:digitalwill")

    # Create final AudioInstruction
    AudioInstruction.objects.create(
        testator=pending_audio.testator,
        audio_file=pending_audio.uploaded_file,
    )

    # Delete pending record after successful verification
    pending_audio.delete()

    messages.success(request, "Audio instruction uploaded successfully.")
    return redirect("administration:digitalwill")


@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_asset_update(request, token):
    try:
        # Validate the token
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification token.")
        return redirect("administration:digitalwill")

    # Retrieve pending update data from session
    data = request.session.get("pending_asset_update")
    if not data:
        messages.error(request, "No pending asset update found.")
        return redirect("administration:digitalwill")

    # Get the testator and corresponding asset
    testator = UserProfile.objects.filter(user=request.user).first()
    asset = get_object_or_404(Asset, id=data['asset_id'], testator=testator)

    # Update asset fields
    asset.asset_type = data['asset_type']
    asset.location = data['location']
    asset.estimated_value = data['estimated_value']
    asset.instruction = data['instruction']

    # If a new image was included, attach it
    if data.get('asset_image_content'):
        image_file = ContentFile(data['asset_image_content'].encode('latin1'), name=data['asset_image_name'])
        asset.asset_image = image_file

    asset.save()

    # Update assigned heirs
    heirs = Heir.objects.filter(id__in=data['assigned_to_ids'])
    asset.assigned_to.set(heirs)

    # Clear session
    request.session.pop("pending_asset_update", None)

    messages.success(request, "Asset successfully updated after verification.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_asset_delete(request, token):
    try:
        # Validate the token
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification token.")
        return redirect("administration:digitalwill")

    # Retrieve pending deletion data from session
    data = request.session.get("pending_asset_delete")
    if not data:
        messages.error(request, "No pending asset deletion request found.")
        return redirect("administration:digitalwill")

    # Get the asset associated with the testator
    testator = UserProfile.objects.filter(user=request.user).first()
    asset = Asset.objects.filter(id=data["asset_id"], testator=testator).first()

    if asset:
        asset.delete()
        messages.success(request, f"Asset '{data['asset_type']}' deleted successfully.")
    else:
        messages.warning(request, "Asset was already deleted or does not exist.")

    # Clear session
    request.session.pop("pending_asset_delete", None)
    return redirect("administration:digitalwill")

@cache_control(no_cache=True, must_revalidate=True, no_store=True, private=True)
@login_required
def dashboardview(request):
    user_profile = request.user.user_userprofile
    get_current_year = timezone.now
    heirs = Heir.objects.filter(testator=user_profile)
    assets = Asset.objects.filter(testator=user_profile)
    special_accounts = SpecialAccount.objects.filter(testator=user_profile)
    confidential_infos = ConfidentialInfo.objects.filter(testator=user_profile)

    total_asset_value = assets.aggregate(total=Sum('estimated_value'))['total'] or 0

    asset_distribution = list(
        assets.values('asset_type').annotate(count=Count('id'))
    )

    heir_distribution = list(
        heirs.values('relationship').annotate(count=Count('id'))
    )

    account_distribution = list(
        special_accounts.values('account_type').annotate(count=Count('id'))
    )

    confidential_distribution = list(
        confidential_infos.annotate(assigned_count=Count('assigned_to')).values('assigned_count')
    )

    asset_data = (
        Asset.objects.filter(testator=request.user.user_userprofile)
        .values('asset_type')
        .annotate(total_value=Sum('estimated_value'))
        .order_by('-total_value')
    )

    labels = [item['asset_type'] or "Unknown" for item in asset_data]
    data = [float(item['total_value']) for item in asset_data]

    context = {
        'labels': labels,
        'data': data,
        'heirs': heirs,
        'assets': assets,
        'special_accounts': special_accounts,
        'confidential_infos': confidential_infos,
        'total_asset_value': total_asset_value,
        'asset_distribution': asset_distribution,
        'heir_distribution': heir_distribution,
        'account_distribution': account_distribution,
        'confidential_distribution': confidential_distribution,
        # counter
        "heir_count": Heir.objects.all().count(),
        "asset_count": Asset.objects.all().count(),
        "confidential_info_count": ConfidentialInfo.objects.all().count(),
        "executor_assigned": Executor.objects.all().exists(),
        "audio_instruction_count": AudioInstruction.objects.all().count(),
        "special_account_count": SpecialAccount.objects.all().count(),
        "pending_verifications": PendingHeirVerification.objects.all().count(),
        "post_death_instructions": PostDeathInstruction.objects.all().exists(),

        "heir_count1": Heir.objects.filter(testator = user_profile).count(),
        "asset_count1": Asset.objects.filter(testator = user_profile).count(),
        "confidential_info_count1": ConfidentialInfo.objects.filter(testator = user_profile).count(),
        "audio_instruction_count1": AudioInstruction.objects.filter(testator = user_profile).count(),

        "special_account_count2": SpecialAccount.objects.filter(testator = user_profile).count(),
        "post_death_instructions2": PostDeathInstruction.objects.filter(testator = user_profile).count(),
        "executor_count2": Executor.objects.filter(testator = user_profile).count(),
        "get_current_year":get_current_year
    }

    return render(request, 'administration/dashboard.html', context)

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def digitalwillview(request):
    get_current_year = timezone.now
    userprofile = UserProfile.objects.filter(user = request.user).first()
    heirs = Heir.objects.filter(testator = userprofile)
    assets = Asset.objects.filter(testator = userprofile)
    asset_instance = Asset.objects.filter(testator = userprofile).first()
    special_accounts = SpecialAccount.objects.filter(testator = userprofile)
    
    confidential_infos = ConfidentialInfo.objects.filter(testator = userprofile)
    post_death_instructions = PostDeathInstruction.objects.filter(testator = userprofile)
    audio_instructions = AudioInstruction.objects.filter(testator = userprofile)
    executors = Executor.objects.filter(testator = userprofile)
    # heir = Heir.objects.filter(id = request.POST.get("assigned_to")).first()
    special_account_instance = SpecialAccount.objects.filter(testator = userprofile).first()
    confidential_info_instance = ConfidentialInfo.objects.filter(testator = userprofile).first()
    executor_instance = Executor.objects.filter(testator = userprofile).first()
    post_death_instructions_instance = PostDeathInstruction.objects.filter(testator = userprofile).first()
    audio_instructions_instance = AudioInstruction.objects.filter(testator = userprofile).first()

    if request.method == "POST" and "add_heir_btn" in request.POST:
        heir_form = HeirForm(request.POST)

        if heir_form.is_valid():
            full_name = heir_form.cleaned_data["full_name"]
            get_heir_by_phone = Heir.objects.filter(phone_number = heir_form.cleaned_data["phone_number"]).first()

            # Prevent duplicate heir for the same testator
            if Heir.objects.filter(full_name__iexact=full_name, testator=userprofile).exists():
                messages.info(request, f"Heir '{full_name}' already exists for this testator.")
                return redirect("administration:digitalwill")
            
            if Heir.objects.filter(phone_number = heir_form.cleaned_data["phone_number"]).exclude(full_name = full_name):
                messages.info(request, f"Heir phone: '{heir_form.cleaned_data["phone_number"]}' already used by other user.")
                return redirect("administration:digitalwill")

            # Generate a unique, signed token
            token = TimestampSigner().sign(str(uuid.uuid4()))

            # Store the heir as a pending verification entry
            PendingHeirVerification.objects.create(
                token=token,
                testator=userprofile,
                full_name=heir_form.cleaned_data["full_name"],
                relationship=heir_form.cleaned_data["relationship"],
                date_of_birth=heir_form.cleaned_data["date_of_birth"],
                phone_number=heir_form.cleaned_data["phone_number"],
            )

            # Build the verification URL
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_heir", kwargs={"token": token})
            )

            # Prepare data and generate PDF
            pending_data = {
                "full_name": heir_form.cleaned_data["full_name"],
                "relationship": heir_form.cleaned_data["relationship"],
                "date_of_birth": heir_form.cleaned_data["date_of_birth"].isoformat(),
                "phone_number": heir_form.cleaned_data["phone_number"],
            }
            pdf_buffer = generate_heir_pdf(pending_data, userprofile)

            # Compose and send the verification email
            email = EmailMessage(
                subject="Verify Heir Addition",
                body=(
                    f"A new heir named {full_name} is being added to your digital will.\n"
                    f"Please verify this addition by clicking the link below:\n\n{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("heir_details.pdf", pdf_buffer.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent. Please confirm to add the heir.")
            return redirect("administration:digitalwill")

        # Form invalid
        messages.error(request, "Something went wrong. Please check the form inputs.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_asset_btn" in request.POST:
        asset_form = AssetForm(request.POST, request.FILES)

        if asset_form.is_valid():
            # Prepare data to store temporarily in session
            asset_data = {
                "asset_type": asset_form.cleaned_data["asset_type"],
                "location": asset_form.cleaned_data["location"],
                "estimated_value": str(asset_form.cleaned_data["estimated_value"]),
                "instruction": asset_form.cleaned_data["instruction"] or "",
                "assigned_to": [str(heir.id) for heir in asset_form.cleaned_data["assigned_to"]],
                "testator_id": str(userprofile.id),
            }

            # Store pending asset in session
            request.session['pending_asset'] = asset_data

            # Generate verification token and URL
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_asset", kwargs={"token": token})
            )

            # Generate PDF summary of asset, including image if uploaded
            image_file = request.FILES.get("asset_image")  # Optional
            pdf_buffer = generate_asset_pdf(asset_data, userprofile.full_name, image_file=image_file)

            # Send verification email
            email = EmailMessage(
                subject="Verify Asset Addition",
                body=(
                    "A new asset is being added to your will.\n\n"
                    f"Please verify this addition by clicking the link below:\n{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("asset_details.pdf", pdf_buffer.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent. Please confirm to add the asset.")
            return redirect("administration:digitalwill")

        # If form is invalid
        messages.error(request, "Something went wrong. Please check the asset form.")
        return redirect("administration:digitalwill")

    if request.method == "POST" and "add_special_account_btn" in request.POST:
        form = SpecialAccountForm(request.POST)

        if form.is_valid():
            # Prepare data for session
            data = {
                "account_type": form.cleaned_data["account_type"],
                "account_name": form.cleaned_data["account_name"],
                "account_number": form.cleaned_data["account_number"],
                "assigned_to_id": str(form.cleaned_data["assigned_to"].id),
                "testator_id": str(userprofile.id),
            }

            # Store in session
            request.session["pending_special_account"] = data

            # Generate token and link
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_special_account", kwargs={"token": token})
            )

            # Generate PDF with branding
            pdf = generate_special_account_pdf(data, userprofile.full_name)

            # Send verification email
            email = EmailMessage(
                subject="Verify Special Account Addition",
                body=(
                    f"You're about to add a special account to your will.\n\n"
                    f"Please verify by clicking the link below:\n{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("special_account.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent. Please check your inbox to confirm.")
            return redirect("administration:digitalwill")

        messages.error(request, "Something went wrong. Please check the special account form.")
        return redirect("administration:digitalwill")
        
    if request.method == "POST" and "add_confidential_info_btn" in request.POST:
        confidential_form = ConfidentialInfoForm(request.POST, request.FILES)
        if confidential_form.is_valid():
            user = request.user
            userprofile = user.user_userprofile

            instructions = confidential_form.cleaned_data["instructions"]
            assigned_heirs = confidential_form.cleaned_data["assigned_to"]  # QuerySet of Heir
            uploaded_file = request.FILES.get("confidential_file")

            # For first-time confidential info, you might create ConfidentialInfo first or handle differently.
            # Here, let's assume you create an empty ConfidentialInfo to link:
            confidential_info = ConfidentialInfo.objects.create(
                testator=userprofile,
                instructions=""  # empty, will be updated on verification
            )

            # Create pending update record
            pending_update = PendingConfidentialInfoUpdate.objects.create(
                confidential_info=confidential_info,
                instructions=instructions,
                user=user,
                created_at=timezone.now(),
            )
            pending_update.assigned_to.set(assigned_heirs)

            if uploaded_file:
                pending_update.uploaded_file.save(uploaded_file.name, uploaded_file)

            # Create signed token for this pending update record
            token = signer.sign(str(pending_update.id))

            verification_url = request.build_absolute_uri(
                reverse("administration:verify_confidential_info", kwargs={"token": token})
            )

            email_subject = "Verify Confidential Info Submission"
            email_body = (
                "A confidential file is about to be submitted.\n"
                "Please confirm by clicking the link below:\n\n"
                f"{verification_url}"
            )

            email = EmailMessage(
                subject=email_subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            if uploaded_file:
                uploaded_file.seek(0)
                email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)

            email.send(fail_silently=False)

            messages.info(request, "Verification email sent. Please confirm to submit confidential info.")
            return redirect("administration:digitalwill")

        messages.error(request, "Invalid form submission.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_executer_btn" in request.POST:
        # Prevent multiple executors per testator
        if Executor.objects.filter(testator=userprofile).exists():
            messages.warning(request, "You already have an executor assigned.")
            return redirect("administration:digitalwill")

        executor_form = ExecutorForm(request.POST)

        if executor_form.is_valid():
            # Prepare data for session storage
            executor_data = {
                "full_name": executor_form.cleaned_data["full_name"],
                "relationship": executor_form.cleaned_data["relationship"],
                "phone_number": executor_form.cleaned_data["phone_number"],
                "testator_id": str(userprofile.id),
            }
            request.session["pending_executor"] = executor_data

            # Generate token and verification URL
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_executor", kwargs={"token": token})
            )

            # Generate PDF summary for email
            pdf = generate_executor_pdf(executor_data, userprofile.full_name)

            # Compose and send verification email
            email = EmailMessage(
                subject="Verify Executor Assignment",
                body=(
                    "You have requested to assign an executor.\n"
                    "Please confirm this action by clicking the link below:\n\n"
                    f"{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("executor_summary.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Confirmation email sent. Please verify to finalize executor assignment.")
            return redirect("administration:digitalwill")

        messages.error(request, f"Form error: {executor_form.errors.as_text()}")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_post_death_instruction_btn" in request.POST:
        instruction_form = PostDeathInstructionForm(request.POST)
        
        if instruction_form.is_valid():
            # Extract instructions from form
            instruction_text = instruction_form.cleaned_data["instructions"]

            # Save instruction data temporarily in session
            data = {
                "instructions": instruction_text,
                "testator_id": str(userprofile.id),
            }
            request.session["pending_instruction"] = data

            # Generate a signed token and verification URL
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_instruction", kwargs={"token": token})
            )

            # Generate a branded PDF summary for email attachment
            pdf = generate_post_death_pdf(data, userprofile.full_name)

            # Compose and send verification email with PDF attached
            email = EmailMessage(
                subject="Verify Post-Death Instruction",
                body=(
                    "You submitted post-death instructions.\n"
                    "Please confirm this action by clicking the link below:\n\n"
                    f"{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("post_death_instructions.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "A confirmation email has been sent. Please verify to finalize submission.")
            return redirect("administration:digitalwill")

        # If form invalid
        messages.error(request, "Please correct the errors in your form.")
        return redirect("administration:digitalwill")

    if request.method == "POST" and "add_audio_instruction_btn" in request.POST:
        audio_form = AudioInstructionForm(request.POST, request.FILES)
        
        if audio_form.is_valid():
            uploaded_audio = request.FILES.get("audio_file")

            if not uploaded_audio:
                messages.error(request, "No audio file uploaded.")
                return redirect("administration:digitalwill")

            # Store audio file content and metadata temporarily in session
            request.session["pending_audio"] = {
                "testator_id": str(userprofile.id),
                "filename": uploaded_audio.name,
                "content_type": uploaded_audio.content_type,
                "file_content": uploaded_audio.read().decode('latin1'),  # encode safely as latin1 string
            }

            # Generate verification token and URL
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_audio", kwargs={"token": token})
            )

            # Send verification email without attachment (file attached after verification)
            email = EmailMessage(
                subject="Verify Audio Instruction Upload",
                body=(
                    "You submitted an audio file.\n"
                    "Please confirm by clicking the link below:\n\n"
                    f"{verification_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.send()

            messages.info(request, "A verification email was sent. Please confirm to complete upload.")
            return redirect("administration:digitalwill")

        # If form invalid
        messages.error(request, "Please correct the form errors.")
        return redirect("administration:digitalwill")

    # Initialize empty forms for creating new entries
    special_account_form = SpecialAccountForm()
    confidential_info_form = ConfidentialInfoForm()
    executor_form = ExecutorForm()
    post_death_instruction_form = PostDeathInstructionForm()
    audio_instruction_form = AudioInstructionForm()
    asset_form = AssetForm()
    heir_form = HeirForm()

    heir_instance = Heir.objects.filter(testator = request.user.user_userprofile).first()
    heir_form_instance = HeirForm(instance = heir_instance)

    # Initialize forms with existing instances for editing
    asset_form_instance = AssetForm(instance=asset_instance)
    special_account_form_instance = SpecialAccountForm(instance=special_account_instance)
    confidential_info_form_instance = ConfidentialInfoForm(instance=confidential_info_instance)
    executor_form_instance = ExecutorForm(instance=executor_instance)
    post_death_instruction_form_instance = PostDeathInstructionForm(instance=post_death_instructions_instance)
    audio_instruction_form_instance = AudioInstructionForm(instance = audio_instructions_instance)

    # Template to render
    templates = "administration/digital_will.html"

    # Context dictionary for template rendering
    context = {
        "special_account_form": special_account_form,
        "confidential_info_form": confidential_info_form,
        "executor_form": executor_form,
        "post_death_instruction_form": post_death_instruction_form,
        "audio_instruction_form": audio_instruction_form,
        "heir_form": heir_form,
        
        "asset_form": asset_form,
        "asset_form_instance": asset_form_instance,
        "special_account_form_instance": special_account_form_instance,
        "confidential_info_form_instance": confidential_info_form_instance,
        "executor_form_instance": executor_form_instance,
        "post_death_instruction_form_instance": post_death_instruction_form_instance,
        "audio_instruction_form_instance":audio_instruction_form_instance,
        "heir_form_instance":heir_form_instance,
        "heir_instance":heir_instance,

        "heirs": heirs,
        "assets": assets,
        "special_accounts": special_accounts,
        "confidential_infos": confidential_infos,
        "executors": executors,
        "post_death_instructions": post_death_instructions,
        "audio_instructions": audio_instructions,
        "get_current_year":get_current_year
    }

    return render(request, templates, context)

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def digitalwillUpdateHeirview(request, heir_id):
    if request.method == "POST" and "update_heir_btn" in request.POST:
        heir = Heir.objects.filter(id=heir_id).first()
        if heir:
            # Update heir details from the submitted form data
            heir.full_name = request.POST.get("full_name")
            heir.relationship = request.POST.get("relationship")
            heir.date_of_birth = request.POST.get("date_of_birth")
            heir.phone_number = request.POST.get("phone_number")
            heir.save()

            messages.success(request, "Heir information was updated successfully!")
        else:
            messages.error(request, "Heir not found.")
        return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def digitalwillDeleteHeirview(request, heir_id):
    if request.method == "POST" and "delete_heir_btn" in request.POST:
        heir = Heir.objects.filter(id=heir_id).first()
        if heir:
            heir.delete()
            messages.success(request, "Heir information was deleted successfully!")
        else:
            messages.error(request, "Heir not found.")
        return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required  
def digitalwillUpdateAssetview(request, asset_id):
    if request.method == "POST" and "update_asset_btn" in request.POST:
        # Get the current testator profile
        testator = UserProfile.objects.filter(user=request.user).first()
        
        # Get the asset to update or return 404 if not found or not owned by testator
        asset = get_object_or_404(Asset, id=asset_id, testator=testator)

        # Bind form with POST data and files, linked to the existing asset instance
        asset_form = AssetForm(request.POST, request.FILES, instance=asset)
        if asset_form.is_valid():
            # Save cleaned form data temporarily in the session for verification step
            request.session['pending_asset_update'] = {
                'asset_id': str(asset.id),
                'asset_type': asset_form.cleaned_data['asset_type'],
                'location': asset_form.cleaned_data['location'],
                'estimated_value': str(asset_form.cleaned_data['estimated_value'] or ''),
                'instruction': asset_form.cleaned_data['instruction'] or '',
                'assigned_to_ids': [str(heir.id) for heir in asset_form.cleaned_data['assigned_to']],
                'asset_image_name': '',
                'asset_image_content': '',
                'asset_image_type': '',
            }

            # If an image file was uploaded, save its details in session
            image_file = request.FILES.get('asset_image')
            if image_file:
                request.session['pending_asset_update']['asset_image_name'] = image_file.name
                request.session['pending_asset_update']['asset_image_content'] = image_file.read().decode('latin1')
                request.session['pending_asset_update']['asset_image_type'] = image_file.content_type

            # Generate a secure token for verification link
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_asset_update", kwargs={"token": token})
            )

            # Optional: Generate a PDF summary for the asset update (uncomment if needed)
            # pdf = generate_asset_update_pdf(request.session['pending_asset_update'], testator.full_name)

            # Send verification email with the confirmation link
            email = EmailMessage(
                subject="Confirm Asset Update",
                body=f"You requested to update the asset: {asset.asset_type}. Please confirm by clicking the link below:\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            # Optionally attach PDF summary if generated
            # email.attach("asset_update_summary.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "A confirmation email has been sent. Please verify to apply changes.")
        else:
            messages.error(request, f"Asset update failed: {asset_form.errors.as_text()}")

        return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def digitalwillDeleteAssetview(request, asset_id):
    if request.method == "POST" and "delete_asset_btn" in request.POST:
        # Get testator profile and asset or 404 if not found/not owned
        testator = UserProfile.objects.filter(user=request.user).first()
        asset = get_object_or_404(Asset, id=asset_id, testator=testator)

        # Store asset details in session for verification step
        request.session["pending_asset_delete"] = {
            "asset_id": str(asset.id),
            "asset_type": asset.asset_type,
            "location": asset.location,
            "estimated_value": str(asset.estimated_value or ''),
            "instruction": asset.instruction or '',
            "asset_image_name": asset.asset_image.name if asset.asset_image else '',
        }

        # Generate verification token and link
        token = signer.sign(str(uuid.uuid4()))
        verification_url = request.build_absolute_uri(
            reverse("administration:verify_asset_delete", kwargs={"token": token})
        )

        # Generate PDF summary of the asset deletion request
        pdf = generate_asset_delete_pdf(request.session["pending_asset_delete"], testator.full_name)

        # Compose the verification email with the PDF summary
        email = EmailMessage(
            subject="Confirm Asset Deletion",
            body=(
                f"You requested to delete the asset: {asset.asset_type}.\n\n"
                f"Please confirm this action by clicking the link below:\n{verification_url}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[request.user.email],
        )
        email.attach("asset_deletion_summary.pdf", pdf.getvalue(), "application/pdf")

        # Attach the asset image file if it exists
        if asset.asset_image:
            with asset.asset_image.open("rb") as img:
                email.attach(asset.asset_image.name, img.read(), asset.asset_image.file.content_type)

        email.send()

        messages.info(request, "A confirmation email with the asset summary was sent. Please verify to complete deletion.")
        return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required    
def digitalwillUpdateSpecialAccountview(request, special_account_id):
    # Get the logged-in user's profile (testator)
    testator = UserProfile.objects.filter(user=request.user).first()
    # Get the SpecialAccount or return 404 if not found or not owned by testator
    special_account = get_object_or_404(SpecialAccount, id=special_account_id, testator=testator)

    if request.method == "POST" and "update_special_account_btn" in request.POST:
        # Bind form to POST data with existing special_account instance
        form = SpecialAccountForm(request.POST, instance=special_account)

        if form.is_valid():
            cleaned = form.cleaned_data

            # Store the update details temporarily in session for verification
            pending_update = {
                'special_account_id': str(special_account.id),
                'account_type': cleaned.get('account_type', ''),
                'account_name': cleaned.get('account_name', ''),
                'account_number': cleaned.get('account_number', ''),
                'assigned_to_id': str(cleaned['assigned_to'].id) if cleaned.get('assigned_to') else '',
            }
            request.session['pending_special_account_update'] = pending_update

            # Generate a signed verification token
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_special_account_update", kwargs={"token": token})
            )
            # Save token in session for later verification
            request.session['special_account_update_token'] = token

            # Prepare and send verification email with clickable link (HTML formatted)
            email_body = f"""
                Dear {request.user.get_full_name()},<br><br>
                You requested to update your Special Account.<br>
                Please verify the changes by clicking the link below:<br>
                <a href="{verification_url}" style="padding:10px 15px; background:#28a745; color:#fff; text-decoration:none;">Verify Account Update</a><br><br>
                If you did not request this, please ignore this email.<br><br>
                Thanks,<br>Your Team
            """

            email = EmailMessage(
                subject="Verify Your Special Account Update",
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.content_subtype = "html"  # Enable HTML email formatting
            email.send()

            messages.info(request, "A verification email has been sent. Please verify to apply the update.")
            return redirect("administration:digitalwill")
        else:
            messages.error(request, f"Update failed: {form.errors.as_text()}")
            return redirect("administration:digitalwill")

    # Redirect if not a POST request or button not clicked
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_special_account_update(request, token):
    # Verify the token signature to ensure it's valid and untampered
    try:
        unsigned_token = signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired verification token.")
        return redirect("administration:digitalwill")

    # Check token matches session token to prevent replay attacks
    session_token = request.session.get('special_account_update_token')
    if not session_token or session_token != token:
        messages.error(request, "Verification token mismatch or expired.")
        return redirect("administration:digitalwill")

    # Retrieve the pending update data from the session
    pending_update = request.session.get('pending_special_account_update')
    if not pending_update:
        messages.error(request, "No pending update found.")
        return redirect("administration:digitalwill")

    # Get the testator and the special account record to update
    testator = UserProfile.objects.filter(user=request.user).first()
    special_account = get_object_or_404(
        SpecialAccount,
        id=pending_update['special_account_id'],
        testator=testator
    )

    # Apply updates from the session data
    special_account.account_type = pending_update.get('account_type', '')
    special_account.account_name = pending_update.get('account_name', '')
    special_account.account_number = pending_update.get('account_number', '')

    assigned_to_id = pending_update.get('assigned_to_id')
    if assigned_to_id:
        assigned_to_heir = Heir.objects.filter(id=assigned_to_id).first()
        special_account.assigned_to = assigned_to_heir
    else:
        special_account.assigned_to = None

    special_account.save()

    # Clear session data related to this update to prevent reuse
    del request.session['pending_special_account_update']
    del request.session['special_account_update_token']

    messages.success(request, "Special Account successfully updated after verification.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
# Request to delete a special account (sends verification email)
def request_delete_special_account(request, special_account_id):
    if request.method == 'POST' and "delete_special_account_btn" in request.POST:
        # Retrieve the special account or 404 if not found
        account = get_object_or_404(SpecialAccount, id=special_account_id)

        # Ensure the logged-in user owns this special account
        if request.user != account.testator.user:
            messages.error(request, "You are not authorized to delete this special account.")
            return redirect('administration:digitalwill')

        # Require email verification before allowing deletion
        if not account.testator.email_verified:
            messages.error(request, "Please verify your email before deleting a special account.")
            return redirect('administration:digitalwill')

        # Create a unique deletion token for verification
        token_obj = SpecialAccountDeleteToken.objects.create(
            special_account=account,
            user=request.user
        )

        # Build a full URL for the user to confirm deletion via email link
        verify_url = request.build_absolute_uri(
            reverse('administration:confirm_delete_special_account', args=[str(token_obj.token)])
        )

        # Compose the verification email content
        email_subject = "Confirm your Special Account deletion"
        email_body = (
            f"Hello {account.testator.full_name},\n\n"
            f"Please click the link below to confirm deletion of your special account '{account.account_name}':\n\n"
            f"{verify_url}\n\n"
            "If you did not request this deletion, please ignore this email."
        )

        # Send the verification email
        email = EmailMessage(
            email_subject,
            email_body,
            to=[account.testator.email]
        )
        email.send(fail_silently=False)

        messages.success(request, "Verification email sent. Please check your inbox to confirm deletion.")
        return redirect('administration:digitalwill')

    # Handle invalid methods or missing form submission
    messages.error(request, "Invalid request method.")
    return redirect('administration:digitalwill')

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
# Confirm deletion via token link (deletes account after verification)
def confirm_delete_special_account(request, token):
    # Fetch the delete token object; ensure it exists and is not used
    token_obj = get_object_or_404(SpecialAccountDeleteToken, token=token, is_used=False)
    account = token_obj.special_account
    testator = account.testator

    # Optional: check if token has expired (24-hour validity)
    expiry_time = token_obj.created_at + timezone.timedelta(hours=24)
    if timezone.now() > expiry_time:
        messages.error(request, "This deletion link has expired.")
        return redirect('administration:digitalwill')

    # Save account name before deletion for confirmation purposes
    account_name = account.account_name
    # Delete the special account
    account.delete()

    # Mark the token as used to prevent reuse
    token_obj.is_used = True
    # token_obj.save()

    # Generate a PDF confirmation of deletion
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 🟧 Header Branding
    p.setFillColor(colors.orange)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, height - 50, "🧾 Digital Will")
    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)

    # 📝 Subtitle
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 100, "Special Account Deletion Confirmation")

    # 🧾 Data Table
    table_data = [
        ["Account Name", account_name],
        ["Deleted By", testator.full_name],
        ["Date", timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ["Confirmation", "The above special account was deleted successfully."]
    ]

    table = Table(table_data, colWidths=[180, 320])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # 🖨️ Draw the table on the canvas
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 280)

    # 🔻 Footer with ISO
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.orange)
    p.drawRightString(width - 50, 30, "ISO 1496177")

    p.showPage()
    p.save()
    buffer.seek(0)

    # Send confirmation email with PDF attached
    email_subject = "Special Account Deletion Confirmed"
    email_body = (
        f"Hello {testator.full_name},\n\n"
        f"Your special account '{account_name}' has been deleted successfully.\n"
        "Please find attached a confirmation PDF."
    )

    email = EmailMessage(
        email_subject,
        email_body,
        to=[testator.email]
    )
    email.attach(f"SpecialAccountDeletion_{account_name}.pdf", buffer.read(), 'application/pdf')
    email.send(fail_silently=False)

    messages.success(request, "Special account deleted and confirmation email sent.")
    return redirect('administration:digitalwill')

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def update_confidential_info(request, id):
    # Get the confidential info object or return 404 if not found
    confidential_info = get_object_or_404(ConfidentialInfo, id=id)

    # Ensure the logged-in user owns this confidential info
    if request.user != confidential_info.testator.user:
        messages.error(request, "You are not authorized.")
        return redirect("administration:digitalwill")

    # Process form submission
    if request.method == 'POST' and "update_confidential_info_btn" in request.POST:
        form = ConfidentialInfoForm(request.POST, request.FILES, instance=confidential_info)
        if form.is_valid():
            # Create a pending update entry (for email verification flow)
            pending_update = PendingConfidentialInfoUpdate.objects.create(
                confidential_info=confidential_info,
                instructions=form.cleaned_data['instructions'],
                user=request.user,
            )
            # Save uploaded file if provided
            pending_update.uploaded_file = form.cleaned_data.get('confidential_file')
            pending_update.save()

            # Save many-to-many 'assigned_to' relation
            pending_update.assigned_to.set(form.cleaned_data['assigned_to'])
            pending_update.save()

            # Generate unique verification link
            uid = urlsafe_base64_encode(force_bytes(request.user.pk))
            token = email_verification_token.make_token(request.user)
            verification_link = request.build_absolute_uri(
                reverse('administration:confirm_update_confidential_info', kwargs={'uidb64': uid, 'token': token})
            )

            # Send verification email to user
            send_mail(
                subject="Confirm Update to Confidential Info",
                message=f"Click the link to confirm the update:\n{verification_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
            )

            messages.success(request, "Check your email to confirm the update.")
            return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required        
def confirm_update_confidential_info(request, uidb64, token):
    # Decode user id and get user
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Verify token and user validity
    if user is not None and email_verification_token.check_token(user, token):
        # Get latest pending update for this user
        pending_update = PendingConfidentialInfoUpdate.objects.filter(user=user).order_by('-created_at').first()

        if not pending_update:
            messages.error(request, "No pending update found.")
            return redirect("administration:digitalwill")

        confidential_info = pending_update.confidential_info

        # Confirm the user owns this confidential info
        if confidential_info.testator.user != user:
            messages.error(request, "Unauthorized update attempt.")
            return redirect("administration:digitalwill")

        # Apply updates from pending update
        confidential_info.instructions = pending_update.instructions
        confidential_info.assigned_to.set(pending_update.assigned_to.all())

        # Update file if a new one was uploaded
        if pending_update.uploaded_file:
            confidential_info.confidential_file.save(
                pending_update.uploaded_file.name,
                pending_update.uploaded_file.file,
                save=False,
            )

        confidential_info.save()

        # Generate PDF summary of the updated confidential info
        html_string = render_to_string('pdf/confidential_info_pdf.html', {
            'confidential_info': confidential_info,
        })
        pdf_file = HTML(string=html_string).write_pdf()
        pdf_io = BytesIO(pdf_file)

        # Email the PDF summary to the user
        email = EmailMessage(
            subject="Confidential Info Updated",
            body="Your confidential info has been successfully updated. The attached PDF contains the summary.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f"confidential_info_{confidential_info.id}.pdf", pdf_io.getvalue(), 'application/pdf')
        email.send()

        # Clean up: delete pending update and associated file
        if pending_update.uploaded_file:
            pending_update.uploaded_file.delete(save=False)
        pending_update.delete()

        messages.success(request, "Your confidential info has been updated. A PDF has been emailed to you.")
        return redirect("administration:digitalwill")

    # Token invalid or expired
    messages.error(request, "Invalid or expired verification link.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_delete_confidential_info(request, id):
    # Get the confidential info object or return 404 if not found
    confidential_info = get_object_or_404(ConfidentialInfo, id=id)

    # Ensure only the owner (testator) can request deletion
    if request.user != confidential_info.testator.user:
        messages.error(request, "You are not authorized to delete this confidential info.")
        return redirect('administration:digitalwill')

    # Generate a unique verification token and encoded user ID for email confirmation link
    uid = urlsafe_base64_encode(force_bytes(request.user.pk))
    token = email_verification_token.make_token(request.user)

    verification_link = request.build_absolute_uri(
        reverse('administration:confirm_delete_confidential_info', kwargs={'uidb64': uid, 'token': token})
    )

    # Send confirmation email to the user with the verification link
    send_mail(
        subject="Confirm Deletion of Confidential Info",
        message=f"Click the link below to confirm deletion of your confidential info:\n\n{verification_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
    )

    messages.success(request, "Verification email sent. Please check your email to confirm deletion.")
    return redirect('administration:digitalwill')

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_delete_confidential_info(request, uidb64, token):
    # Decode the user ID from the URL parameter and retrieve the user
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Validate token and user authenticity
    if user is not None and email_verification_token.check_token(user, token):
        # Retrieve the confidential info associated with this user (latest entry)
        confidential_info = ConfidentialInfo.objects.filter(testator__user=user).order_by('-created_at').first()

        if not confidential_info:
            messages.error(request, "No confidential info found to delete.")
            return redirect('administration:digitalwill')

        # Generate a PDF summary of the confidential info before deleting
        html_string = render_to_string('pdf/confidential_info_pdf.html', {
            'confidential_info': confidential_info,
        })
        pdf_file = HTML(string=html_string).write_pdf()
        pdf_io = BytesIO(pdf_file)

        # Send an email with the PDF summary attached confirming deletion
        email = EmailMessage(
            subject="Confidential Info Deleted",
            body="Your confidential info has been deleted. Attached is a PDF summary of the deleted info.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f"deleted_confidential_info_{confidential_info.id}.pdf", pdf_io.getvalue(), 'application/pdf')
        email.send()

        # Delete the confidential info from the database
        confidential_info.delete()

        messages.success(request, "Confidential info deleted and PDF summary emailed.")
        return redirect('administration:digitalwill')

    # If the token is invalid or expired, notify the user
    messages.error(request, "Invalid or expired verification link.")
    return redirect('administration:digitalwill')

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_update_executor(request, id):
    # Get the Executor object or return 404 if not found
    executor = get_object_or_404(Executor, id=id)

    # Only allow the owner (testator) to update this executor
    if request.user != executor.testator.user:
        messages.error(request, "You are not authorized.")
        return redirect('administration:digitalwill')

    if request.method == 'POST':
        form = ExecutorForm(request.POST, instance=executor)
        if form.is_valid():
            # Save the form data temporarily in the session for confirmation
            request.session['pending_executor_update'] = {
                'id': str(executor.id),
                'full_name': form.cleaned_data['full_name'],
                'relationship': form.cleaned_data['relationship'],
                'phone_number': form.cleaned_data['phone_number'],
            }

            # Generate a secure token and user ID for email verification
            uid = urlsafe_base64_encode(force_bytes(request.user.pk))
            token = email_verification_token.make_token(request.user)

            # Build the URL user will click to confirm the update
            confirm_url = request.build_absolute_uri(
                reverse('administration:confirm_update_executor', kwargs={'uidb64': uid, 'token': token})
            )

            # Send confirmation email with the verification link
            send_mail(
                subject="Confirm Executor Update",
                message=f"Click the link below to confirm the update to your Executor:\n\n{confirm_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
            )

            messages.success(request, "Verification link sent to your email.")
            return redirect('administration:digitalwill')
    else:
        form = ExecutorForm(instance=executor)

    # Render the form page if GET or form is invalid
    return render(request, 'administration/digital_will.html', {'form': form, 'executor': executor})


@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_update_executor(request, uidb64, token):
    # Decode user ID from the URL and get the user object
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify token and user
    if user is not None and email_verification_token.check_token(user, token):
        # Retrieve pending update data from session
        pending = request.session.get('pending_executor_update')
        if not pending:
            messages.error(request, "No pending update found.")
            return redirect('administration:digitalwill')

        # Get the Executor object to update
        executor = get_object_or_404(Executor, id=pending['id'])

        # Confirm the user owns this executor
        if executor.testator.user != user:
            messages.error(request, "Unauthorized action.")
            return redirect('administration:digitalwill')

        # Apply the update to the Executor
        executor.full_name = pending['full_name']
        executor.relationship = pending['relationship']
        executor.phone_number = pending['phone_number']
        executor.save()

        # Generate PDF summary of the updated Executor info
        html = render_to_string('pdf/executor_summary.html', {'executor': executor})
        pdf_file = HTML(string=html).write_pdf()
        pdf_io = BytesIO(pdf_file)

        # Send an email with the PDF attached as confirmation
        email = EmailMessage(
            subject="Executor Information Updated",
            body="Attached is the updated Executor info.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f"executor_update_{executor.id}.pdf", pdf_io.getvalue(), 'application/pdf')
        email.send()

        # Remove the pending update from session after successful update
        del request.session['pending_executor_update']

        messages.success(request, "Executor updated and confirmation PDF sent.")
        return redirect('administration:digitalwill')

    # If token or user invalid, show error
    messages.error(request, "Invalid or expired confirmation link.")
    return redirect('administration:digitalwill')

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_delete_executor(request, id):
    # Get the executor or 404 if not found
    executor = get_object_or_404(Executor, id=id)

    # Only allow the owner (testator) to delete this executor
    if request.user != executor.testator.user:
        messages.error(request, "You are not authorized to delete this executor.")
        return redirect("administration:digitalwill")

    # Save the executor ID in the session to confirm deletion later
    request.session["pending_executor_delete_id"] = str(executor.id)

    # Generate a secure token and encode user ID for email verification
    uid = urlsafe_base64_encode(force_bytes(request.user.pk))
    token = email_verification_token.make_token(request.user)

    # Build confirmation URL for user to confirm deletion
    confirm_url = request.build_absolute_uri(
        reverse('yourapp:confirm_delete_executor', kwargs={'uidb64': uid, 'token': token})
    )

    # Send confirmation email with the verification link
    send_mail(
        subject="Confirm Executor Deletion",
        message=f"Click to confirm deletion of executor:\n{confirm_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
    )

    messages.success(request, "A confirmation link has been sent to your email.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_delete_executor(request, uidb64, token):
    # Decode user ID from the URL and get the user
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify token and user
    if user is not None and email_verification_token.check_token(user, token):
        # Get executor ID from session to confirm which executor to delete
        executor_id = request.session.get("pending_executor_delete_id")
        if not executor_id:
            messages.error(request, "No pending deletion found.")
            return redirect("administration:digitalwill")

        # Fetch the executor object
        executor = get_object_or_404(Executor, id=executor_id)

        # Confirm the user owns this executor
        if executor.testator.user != user:
            messages.error(request, "Unauthorized deletion attempt.")
            return redirect("administration:digitalwill")

        # Generate a PDF summary of the executor before deleting
        html = render_to_string("pdf/executor_summary.html", {"executor": executor})
        pdf_file = HTML(string=html).write_pdf()
        pdf_io = BytesIO(pdf_file)

        # Delete the executor record
        executor.delete()

        # Email the confirmation PDF to the user
        email = EmailMessage(
            subject="Executor Deleted",
            body="Your executor has been deleted. See attached summary.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f"executor_deleted_{executor_id}.pdf", pdf_io.getvalue(), "application/pdf")
        email.send()

        # Remove executor ID from session after successful deletion
        del request.session["pending_executor_delete_id"]

        messages.success(request, "Executor deleted. A confirmation PDF has been emailed.")
        return redirect("administration:digitalwill")

    # If token or user invalid, show error message
    messages.error(request, "Invalid or expired confirmation link.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_update_post_death(request, id):
    # Retrieve the post-death instruction for the logged-in user (testator)
    instruction = get_object_or_404(PostDeathInstruction, testator__user=request.user)

    if request.method == 'POST':
        # Bind form data to the existing instruction instance
        form = PostDeathInstructionForm(request.POST, instance=instruction)
        if form.is_valid():
            # Save update details temporarily in session for email confirmation
            request.session['pending_post_death'] = {
                'id': str(instruction.id),
                'instructions': form.cleaned_data['instructions'],
            }

            # Generate encoded user ID and secure email verification token
            uid = urlsafe_base64_encode(force_bytes(request.user.pk))
            token = email_verification_token.make_token(request.user)

            # Build absolute URL for user to confirm the update
            link = request.build_absolute_uri(
                reverse('administration:confirm_update_post_death', kwargs={'uidb64': uid, 'token': token})
            )

            # Send verification email containing the confirmation link
            send_mail(
                subject="Confirm Update to Post-Death Instructions",
                message=f"Click the link to confirm:\n{link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
            )

            messages.success(request, "Verification email sent.")
            return redirect("administration:digitalwill")
    else:
        # If GET request, display form with existing data
        form = PostDeathInstructionForm(instance=instruction)

    return render(request, 'administration.html', {'form': form})

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_update_post_death(request, uidb64, token):
    try:
        # Decode user ID and retrieve user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify token and user validity
    if user and email_verification_token.check_token(user, token):
        # Retrieve pending update details from session
        pending = request.session.get('pending_post_death')
        if not pending:
            messages.error(request, "No pending update found.")
            return redirect("administration:digitalwill")

        # Get the specific post-death instruction record
        instruction = get_object_or_404(PostDeathInstruction, id=pending['id'])

        # Check if the instruction belongs to the authenticated user
        if instruction.testator.user != user:
            messages.error(request, "Unauthorized update attempt.")
            return redirect("administration:digitalwill")

        # Apply the updates and save
        instruction.instructions = pending['instructions']
        instruction.save()

        # Render a PDF summary of the updated instructions
        html = render_to_string('pdf/post_death_summary.html', {'instruction': instruction})
        pdf = HTML(string=html).write_pdf()
        buffer = BytesIO(pdf)

        # Email the PDF summary to the user
        email = EmailMessage(
            subject="Post-Death Instructions Updated",
            body="Attached is the updated post-death instruction.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f'post_death_{instruction.id}.pdf', buffer.getvalue(), 'application/pdf')
        email.send()

        # Clear the pending update from session after confirmation
        del request.session['pending_post_death']
        messages.success(request, "Post-death instructions updated and emailed.")
        return redirect("administration:digitalwill")

    # If token or user invalid, show error message
    messages.error(request, "Invalid or expired verification link.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_delete_post_death_instruction(request, id):
    # Get the post-death instruction object or show 404 if not found
    instruction = get_object_or_404(PostDeathInstruction, id=id)

    # Ensure the logged-in user owns this instruction
    if request.user != instruction.testator.user:
        messages.error(request, "Unauthorized action.")
        return redirect("administration:digitalwill")

    # Store the ID of the instruction to be deleted in the session temporarily
    request.session["pending_post_death_delete_id"] = str(instruction.id)

    # Generate user ID and email verification token for secure confirmation link
    uid = urlsafe_base64_encode(force_bytes(request.user.pk))
    token = email_verification_token.make_token(request.user)

    # Build full confirmation URL to send in email
    link = request.build_absolute_uri(
        reverse('administration:confirm_delete_post_death_instruction', kwargs={'uidb64': uid, 'token': token})
    )

    # Send verification email with confirmation link
    send_mail(
        subject="Confirm Deletion of Post-Death Instruction",
        message=f"Click this link to confirm deletion:\n{link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
    )

    messages.success(request, "Check your email to confirm deletion.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_delete_post_death_instruction(request, uidb64, token):
    try:
        # Decode the user ID and fetch the user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify that the user and token are valid
    if user and email_verification_token.check_token(user, token):
        # Retrieve the ID of the instruction pending deletion from the session
        instruction_id = request.session.get("pending_post_death_delete_id")
        if not instruction_id:
            messages.error(request, "No pending deletion found.")
            return redirect("administration:digitalwill")

        # Retrieve the instruction object or 404
        instruction = get_object_or_404(PostDeathInstruction, id=instruction_id)

        # Confirm the instruction belongs to the authenticated user
        if instruction.testator.user != user:
            messages.error(request, "Unauthorized.")
            return redirect("administration:digitalwill")

        # Generate PDF summary of the instruction before deleting it
        html = render_to_string("pdf/post_death_deleted_summary.html", {'instruction': instruction})
        pdf = HTML(string=html).write_pdf()
        pdf_io = BytesIO(pdf)

        # Delete the instruction from the database
        instruction.delete()

        # Send an email to confirm deletion with the PDF summary attached
        email = EmailMessage(
            subject="Post-Death Instruction Deleted",
            body="Your instruction has been deleted. See the summary attached.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f'post_death_deleted_{instruction_id}.pdf', pdf_io.getvalue(), 'application/pdf')
        email.send()

        # Clear the session data for pending deletion
        del request.session["pending_post_death_delete_id"]

        messages.success(request, "Instruction deleted. A PDF has been emailed.")
        return redirect("administration:digitalwill")

    # Handle invalid or expired confirmation links
    messages.error(request, "Invalid or expired confirmation link.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_update_audio_instruction(request, id):
    # Retrieve the AudioInstruction object or 404 if not found
    audio = get_object_or_404(AudioInstruction, id=id)

    # Check that the current user is the owner
    if request.user != audio.testator.user:
        messages.error(request, "Unauthorized.")
        return redirect("administration:digitalwill")

    # Handle POST request with an uploaded audio file
    if request.method == 'POST' and request.FILES.get('audio_file'):
        file = request.FILES['audio_file']

        # Save the uploaded file temporarily
        temp_path = f'temp_audio/{uuid.uuid4()}_{file.name}'
        saved_path = default_storage.save(temp_path, file)

        # Store pending update info in session for later confirmation
        request.session['pending_audio_update'] = {
            'audio_id': str(audio.id),
            'temp_audio_path': saved_path,
        }

        # Create secure verification token and URL
        uid = urlsafe_base64_encode(force_bytes(request.user.pk))
        token = email_verification_token.make_token(request.user)
        link = request.build_absolute_uri(
            reverse('administration:confirm_update_audio_instruction', kwargs={'uidb64': uid, 'token': token})
        )

        # Send confirmation email with the verification link
        send_mail(
            subject="Confirm Audio Update",
            message=f"Click to confirm the audio update:\n{link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
        )

        messages.success(request, "Check your email to confirm the update.")
        return redirect("administration:digitalwill")

    # If no file uploaded or wrong method, show error and redirect
    messages.error(request, "No file uploaded.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_update_audio_instruction(request, uidb64, token):
    try:
        # Decode the user ID and fetch the user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify the user and token are valid
    if user and email_verification_token.check_token(user, token):
        # Retrieve the pending update info from session
        pending = request.session.get('pending_audio_update')
        if not pending:
            messages.error(request, "No pending update found.")
            return redirect("administration:digitalwill")

        # Retrieve the audio instruction object
        audio = get_object_or_404(AudioInstruction, id=pending['audio_id'])

        # Verify ownership again
        if audio.testator.user != user:
            messages.error(request, "Unauthorized.")
            return redirect("administration:digitalwill")

        # Open the temporary file and save it to the final audio_file field
        temp_path = pending['temp_audio_path']
        with default_storage.open(temp_path, 'rb') as new_file:
            audio.audio_file.save(os.path.basename(temp_path), new_file)

        audio.save()

        # Generate PDF summary of the updated audio instruction
        html = render_to_string("pdf/audio_instruction_updated_summary.html", {'audio': audio})
        pdf = HTML(string=html).write_pdf()
        pdf_io = BytesIO(pdf)

        # Send confirmation email with PDF attachment
        email = EmailMessage(
            subject="Audio Instruction Updated",
            body="Your audio has been updated. See attached summary.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f"audio_updated_{audio.id}.pdf", pdf_io.getvalue(), 'application/pdf')
        email.send()

        # Clean up: delete temp file and clear session data
        default_storage.delete(temp_path)
        del request.session['pending_audio_update']

        messages.success(request, "Audio updated successfully.")
        return redirect("administration:digitalwill")

    # If verification link is invalid or expired
    messages.error(request, "Invalid or expired verification link.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def request_delete_audio_instruction(request, id):
    # Retrieve the audio instruction or return 404 if not found
    audio = get_object_or_404(AudioInstruction, id=id)

    # Ensure the current user owns the audio instruction
    if request.user != audio.testator.user:
        messages.error(request, "Unauthorized.")
        return redirect("administration:digitalwill")

    # Store the audio ID in session for confirmation later
    request.session["pending_audio_delete_id"] = str(audio.id)

    # Generate verification token and link for email confirmation
    uid = urlsafe_base64_encode(force_bytes(request.user.pk))
    token = email_verification_token.make_token(request.user)
    link = request.build_absolute_uri(
        reverse('administration:confirm_delete_audio_instruction', kwargs={'uidb64': uid, 'token': token})
    )

    # Send an email with the confirmation link
    send_mail(
        subject="Confirm Deletion of Audio Instruction",
        message=f"Click the link to confirm deletion:\n{link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
    )

    messages.success(request, "Confirmation link sent to your email.")
    return redirect("administration:digitalwill")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def confirm_delete_audio_instruction(request, uidb64, token):
    try:
        # Decode the user ID from the link and fetch the user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    # Verify the user and token are valid
    if user and email_verification_token.check_token(user, token):
        # Get the audio ID stored in session during the delete request
        audio_id = request.session.get("pending_audio_delete_id")
        if not audio_id:
            messages.error(request, "No pending deletion found.")
            return redirect("administration:digitalwill")

        # Fetch the audio instruction object
        audio = get_object_or_404(AudioInstruction, id=audio_id)

        # Verify ownership again before deleting
        if audio.testator.user != user:
            messages.error(request, "Unauthorized.")
            return redirect("administration:digitalwill")

        # Generate a PDF summary before deletion for record
        html = render_to_string("pdf/audio_instruction_deleted_summary.html", {'audio': audio})
        pdf_file = HTML(string=html).write_pdf()
        buffer = BytesIO(pdf_file)

        # Delete the audio instruction
        audio.delete()

        # Email the user a confirmation with the PDF summary attached
        email = EmailMessage(
            subject="Audio Instruction Deleted",
            body="Your audio instruction has been deleted. See attached PDF summary.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach(f'audio_deleted_{audio_id}.pdf', buffer.getvalue(), 'application/pdf')
        email.send()

        # Clean up the session
        del request.session["pending_audio_delete_id"]

        messages.success(request, "Audio instruction deleted and PDF emailed.")
        return redirect("administration:digitalwill")

    # Handle invalid or expired verification links
    messages.error(request, "Invalid or expired link.")
    return redirect("administration:digitalwill")

def beneficiaryview(request):
    get_current_year = timezone.now
    userprofile = UserProfile.objects.filter(user = request.user).first()
    assets = Asset.objects.filter(testator = userprofile)
    special_accounts = SpecialAccount.objects.filter(testator = userprofile)
    
    confidential_infos = ConfidentialInfo.objects.filter(testator = userprofile)
    post_death_instructions = PostDeathInstruction.objects.filter(testator = userprofile)
    audio_instructions = AudioInstruction.objects.filter(testator = userprofile)
    templates = "administration/beneficiary.html"

    # Context dictionary for template rendering
    context = {
        "assets": assets,
        "special_accounts": special_accounts,
        "confidential_infos": confidential_infos,
        "post_death_instructions": post_death_instructions,
        "audio_instructions": audio_instructions,
        "get_current_year":get_current_year
    }
    return render(request, templates, context)