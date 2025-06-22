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

signer = TimestampSigner()
TOKEN_EXPIRY_SECONDS = 86400  # 1 day
# Create your views here.
def verify_heir_view(request, token):
    try:
        signer.unsign(token, max_age=86400)  # expires in 1 day
        pending = request.session.get("pending_heir")

        if not pending:
            messages.error(request, "No pending heir found.")
            return redirect("administration:digitalwill")

        testator = get_object_or_404(UserProfile, id=pending["testator_id"])

        Heir.objects.create(
            testator=testator,
            full_name=pending["full_name"],
            relationship=pending["relationship"],
            date_of_birth=pending["date_of_birth"],
            phone_number=pending["phone_number"],
        )

        # Clear from session
        del request.session["pending_heir"]

        messages.success(request, f"Heir '{pending['full_name']}' was successfully verified and added.")
        return redirect("administration:digitalwill")

    except SignatureExpired:
        messages.error(request, "Verification link expired.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")

    return redirect("administration:digitalwill")

def verify_asset_view(request, token):
    try:
        signer.unsign(token, max_age=86400)  # link expires in 1 day
        pending = request.session.get("pending_asset")

        if not pending:
            messages.error(request, "No pending asset data found.")
            return redirect("administration:digitalwill")

        testator = get_object_or_404(UserProfile, id=pending["testator_id"])
        asset = Asset.objects.create(
            testator=testator,
            asset_type=pending["asset_type"],
            location=pending["location"],
            estimated_value=pending["estimated_value"],
            instruction=pending["instruction"],
        )

        # Link heirs
        heirs = Heir.objects.filter(id__in=pending["assigned_to"])
        asset.assigned_to.set(heirs)
        asset.save()

        del request.session["pending_asset"]
        messages.success(request, "Asset successfully verified and added.")
        return redirect("administration:digitalwill")

    except SignatureExpired:
        messages.error(request, "Verification link has expired.")
    except BadSignature:
        messages.error(request, "Invalid verification token.")

    return redirect("administration:digitalwill")

def resend_asset_verification_email(request):
    pending = request.session.get("pending_asset")
    if not pending:
        messages.error(request, "No pending asset found to resend.")
        return redirect("administration:digitalwill")

    testator = get_object_or_404(UserProfile, id=pending["testator_id"])

    # Generate token and verification link
    token = signer.sign(str(uuid.uuid4()))
    verification_url = request.build_absolute_uri(
        reverse("administration:verify_asset", kwargs={"token": token})
    )

    # Optional: fetch from previously uploaded files if kept in memory
    image_file = None  # only possible if stored or reuploaded

    pdf_buffer = generate_asset_pdf(pending, testator.full_name, image_file=image_file)

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

def verify_special_account(request, token):
    try:
        signer.unsign(token, max_age=TOKEN_EXPIRY_SECONDS)
        pending = request.session.get("pending_special_account")
        if not pending:
            messages.error(request, "No pending account found.")
            return redirect("administration:digitalwill")

        testator = get_object_or_404(UserProfile, id=pending["testator_id"])
        heir = get_object_or_404(Heir, id=pending["assigned_to_id"])

        SpecialAccount.objects.create(
            testator=testator,
            account_type=pending["account_type"],
            account_name=pending["account_name"],
            account_number=pending["account_number"],
            assigned_to=heir,
        )

        del request.session["pending_special_account"]
        messages.success(request, "Special Account verified and added successfully.")
    except SignatureExpired:
        messages.error(request, "Verification link expired, please resend.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")

    return redirect("administration:digitalwill")

def resend_special_account_verification(request):
    # Check for pending special account data in session
    pending = request.session.get("pending_special_account")
    if not pending:
        messages.error(request, "No pending special account to resend verification for.")
        return redirect("administration:digitalwill")

    # Get testator info for PDF branding
    testator_id = pending.get("testator_id")
    userprofile = get_object_or_404(UserProfile, id=testator_id)

    # Create a new signed token and verification URL
    token = signer.sign(str(uuid.uuid4()))
    verification_url = request.build_absolute_uri(
        reverse("administration:verify_special_account", kwargs={"token": token})
    )

    # Generate PDF with branding from pending data
    pdf_buffer = generate_special_account_pdf(pending, userprofile.full_name)

    # Prepare and send the verification email with PDF attachment
    email = EmailMessage(
        subject="Resend: Verify Special Account Addition",
        body=f"""
        Hello {userprofile.full_name},

        You requested to add a special account. Please verify this action by clicking the link below:

        {verification_url}

        If you did not initiate this, please ignore this email.

        Thank you,
        Your Digital Will Team
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    email.attach("special_account.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.success(request, "Verification email resent successfully. Please check your inbox.")
    return redirect("administration:digitalwill")

def verify_confidential_info(request, token):
    try:
        signer.unsign(token, max_age=TOKEN_EXPIRY_SECONDS)

        pending = request.session.get("pending_confidential_info")
        if not pending:
            messages.error(request, "No pending confidential info found.")
            return redirect("administration:digitalwill")

        testator = get_object_or_404(UserProfile, id=pending["testator_id"])
        heir = get_object_or_404(Heir, id=pending["assigned_to_id"])

        ConfidentialInfo.objects.create(
            testator=testator,
            instructions=pending["instructions"],
            assigned_to=heir,
            # Note: confidential_file must be uploaded again or stored temporarily
        )

        del request.session["pending_confidential_info"]
        messages.success(request, "Confidential info verified and saved.")
    except SignatureExpired:
        messages.error(request, "Verification link expired.")
    except BadSignature:
        messages.error(request, "Invalid or tampered verification link.")

    return redirect("administration:digitalwill")

def resend_confidential_info_verification(request):
    # ✅ Check if there's a pending confidential info in session
    pending = request.session.get("pending_confidential_info")
    if not pending:
        messages.error(request, "No pending confidential info to resend verification for.")
        return redirect("administration:digitalwill")

    # ✅ Get testator to generate PDF branding
    testator_id = pending.get("testator_id")
    userprofile = get_object_or_404(UserProfile, id=testator_id)

    # ✅ Generate token + link
    token = signer.sign(str(uuid.uuid4()))
    verification_url = request.build_absolute_uri(
        reverse("administration:verify_confidential_info", kwargs={"token": token})
    )

    # ✅ Generate branded PDF
    pdf_buffer = generate_confidential_info_pdf(pending, userprofile.full_name)

    # ✅ Send email with PDF
    email = EmailMessage(
        subject="Resend: Verify Confidential Info Submission",
        body=f"""
        Hello {userprofile.full_name},

        You requested to add confidential information. 
        To confirm, please click the link below:

        {verification_url}

        If you did not request this, you can ignore this email.

        Thank you,
        Your Digital Will Team
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    email.attach("confidential_info.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.success(request, "Verification email resent successfully. Please check your inbox.")
    return redirect("administration:digitalwill")

def verify_executor(request, token):
    try:
        # Verify the token
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired token.")
        return redirect("administration:digitalwill")

    data = request.session.get("pending_executor")
    if not data:
        messages.error(request, "No executor data found.")
        return redirect("administration:digitalwill")

    # Save to database
    testator = UserProfile.objects.get(id=data["testator_id"])
    Executor.objects.create(
        testator=testator,
        full_name=data["full_name"],
        relationship=data["relationship"],
        phone_number=data["phone_number"],
    )

    # Clean session
    request.session.pop("pending_executor", None)

    messages.success(request, "Executor has been successfully added.")
    return redirect("administration:digitalwill")

def verify_instruction(request, token):
    try:
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired token.")
        return redirect("administration:digitalwill")

    data = request.session.get("pending_instruction")
    if not data:
        messages.error(request, "No instruction data found.")
        return redirect("administration:digitalwill")

    testator = UserProfile.objects.get(id=data["testator_id"])

    # Ensure only one instruction exists
    PostDeathInstruction.objects.update_or_create(
        testator=testator,
        defaults={"instructions": data["instructions"]}
    )

    # Clear session
    request.session.pop("pending_instruction", None)

    messages.success(request, "Post-death instructions have been saved.")
    return redirect("administration:digitalwill")

def verify_audio(request, token):
    try:
        signer.unsign(token)
    except BadSignature:
        messages.error(request, "Invalid or expired token.")
        return redirect("administration:digitalwill")

    data = request.session.get("pending_audio")
    if not data:
        messages.error(request, "No pending audio found.")
        return redirect("administration:digitalwill")

    # Reconstruct file
    from django.core.files.base import ContentFile
    testator = UserProfile.objects.get(id=data["testator_id"])
    file_data = data["file_content"].encode('latin1')
    audio_file = ContentFile(file_data, name=data["filename"])

    # Save model
    AudioInstruction.objects.create(
        testator=testator,
        audio_file=audio_file,
    )

    # Clean session
    request.session.pop("pending_audio", None)

    messages.success(request, "Audio instruction uploaded successfully.")
    return redirect("administration:digitalwill")

def dashboardview(request):
    templates = "administration/dashboard.html"
    context = {}
    return render(request, templates, context)

def generate_heir_verification_token(data):
    return signer.sign(data)

def digitalwillview(request):
    userprofile = UserProfile.objects.filter(user = request.user).first()
    heirs = Heir.objects.filter(testator = userprofile)
    assets = Asset.objects.filter(testator = userprofile)
    asset_instance = Asset.objects.filter(testator = userprofile).first()
    special_accounts = SpecialAccount.objects.filter(testator = userprofile)
    confidential_infos = ConfidentialInfo.objects.filter(testator = userprofile)
    post_death_instructions = PostDeathInstruction.objects.filter(testator = userprofile)
    audio_instructions = AudioInstruction.objects.filter(testator = userprofile)
    executors = Executor.objects.filter(testator = userprofile)
    heir = Heir.objects.filter(id = request.POST.get("assigned_to")).first()

    if request.method == "POST" and "add_heir_btn" in request.POST:
        heir_form = HeirForm(request.POST)
        if heir_form.is_valid():
            full_name = heir_form.cleaned_data["full_name"]

            # Prevent duplicate heir for this testator
            if Heir.objects.filter(full_name__iexact=full_name, testator=userprofile).exists():
                messages.info(request, f"Heir '{full_name}' already exists for this testator.")
                return redirect("administration:digitalwill")

            # Store pending data in session
            pending_data = {
                "full_name": heir_form.cleaned_data["full_name"],
                "relationship": heir_form.cleaned_data["relationship"],
                "date_of_birth": heir_form.cleaned_data["date_of_birth"].isoformat(),
                "phone_number": heir_form.cleaned_data["phone_number"],
                "testator_id": str(userprofile.id),
            }

            request.session['pending_heir'] = pending_data

            # Generate token and URL
            token = generate_heir_verification_token(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_heir", kwargs={"token": token})
            )

            # Generate PDF
            pdf_buffer = generate_heir_pdf(pending_data, userprofile)

            # Compose email with PDF
            email = EmailMessage(
                subject="Verify Heir Addition",
                body=f"A new heir named {full_name} is being added.\nPlease confirm by clicking the link below:\n\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("heir_details.pdf", pdf_buffer.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent with PDF attached. Please confirm to add the heir.")
            return redirect("administration:digitalwill")

        messages.error(request, "Something went wrong. Please check the form.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_asset_btn" in request.POST:
        asset_form = AssetForm(request.POST, request.FILES)
        if asset_form.is_valid():
            asset_data = {
                "asset_type": asset_form.cleaned_data["asset_type"],
                "location": asset_form.cleaned_data["location"],
                "estimated_value": str(asset_form.cleaned_data["estimated_value"]),
                "instruction": asset_form.cleaned_data["instruction"] or "",
                "assigned_to": [str(heir.id) for heir in asset_form.cleaned_data["assigned_to"]],
                "testator_id": str(userprofile.id),
            }

            request.session['pending_asset'] = asset_data
            # Pass uploaded image if available
            image_file = request.FILES.get("asset_image")
            pdf_buffer = generate_asset_pdf(asset_data, userprofile.full_name, image_file=image_file)

            # Create verification link
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_asset", kwargs={"token": token})
            )

            # Generate PDF
            pdf_buffer = generate_asset_pdf(asset_data, testator_name=userprofile.full_name)

            # Email with PDF
            email = EmailMessage(
                subject="Verify Asset Addition",
                body=f"A new asset is being added.\n\nPlease confirm by clicking the link below:\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("asset_details.pdf", pdf_buffer.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent. Please confirm to add the asset.")
            return redirect("administration:digitalwill")

        messages.error(request, "Something went wrong. Please check the form.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_special_account_btn" in request.POST:
        form = SpecialAccountForm(request.POST)
        if form.is_valid():
            data = {
                "account_type": form.cleaned_data["account_type"],
                "account_name": form.cleaned_data["account_name"],
                "account_number": form.cleaned_data["account_number"],
                "assigned_to_id": str(form.cleaned_data["assigned_to"].id),
                "testator_id": str(userprofile.id),
            }
            request.session["pending_special_account"] = data

            token = signer.sign(str(uuid.uuid4()))
            url = request.build_absolute_uri(
                reverse("administration:verify_special_account", kwargs={"token": token})
            )

            pdf = generate_special_account_pdf(data, userprofile.full_name)

            email = EmailMessage(
                subject="Verify Special Account Addition",
                body=f"Please verify the account by clicking this link:\n\n{url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("special_account.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "Verification email sent with PDF attached. Please check your inbox.")
            return redirect("administration:digitalwill")
        messages.error(request, "Something went wrong. Please check the form.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_confidential_btn" in request.POST:
        confidential_form = ConfidentialInfoForm(request.POST, request.FILES)
        if confidential_form.is_valid():
            data = {
                "instructions": confidential_form.cleaned_data["instructions"],
                "assigned_to_id": str(confidential_form.cleaned_data["assigned_to"].id),
                "testator_id": str(userprofile.id),
            }

            # Save file temporarily in session (just the name for reference)
            uploaded_file = request.FILES.get("confidential_file")
            request.session["pending_confidential"] = data
            request.session["confidential_filename"] = uploaded_file.name if uploaded_file else None
            request.session["confidential_file_content"] = uploaded_file.read().decode('latin1') if uploaded_file else None

            # Generate token and link
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_confidential", kwargs={"token": token})
            )

            # PDF branding
            pdf = generate_confidential_pdf(data, userprofile.full_name)

            # Email
            email = EmailMessage(
                subject="Verify Confidential Info Submission",
                body=f"A confidential file is about to be submitted. Please confirm this action by clicking the link below:\n\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("confidential_summary.pdf", pdf.getvalue(), "application/pdf")
            if uploaded_file:
                email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)
            email.send()

            messages.info(request, "Verification email sent. Please confirm to submit confidential info.")
            return redirect("administration:digitalwill")

        messages.error(request, "Something went wrong. Please check your submission.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_executor_btn" in request.POST:
        if Executor.objects.filter(testator=userprofile).exists():
            messages.warning(request, "You already have an executor assigned.")
            return redirect("administration:digitalwill")

        executor_form = ExecutorForm(request.POST)
        if executor_form.is_valid():
            # Prepare cleaned form data
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

            # 🔽 PDF generation goes here
            pdf = generate_executor_pdf(executor_data, userprofile.full_name)

            # Compose and send email
            email = EmailMessage(
                subject="Verify Executor Assignment",
                body=f"You have requested to assign an executor. "
                    f"Please confirm this action by clicking the link below:\n\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("executor_summary.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "A confirmation email has been sent. Please verify to finalize executor assignment.")
            return redirect("administration:digitalwill")

        messages.error(request, f"Form error: {executor_form.errors.as_text()}")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_instruction_btn" in request.POST:
        instruction_form = PostDeathInstructionForm(request.POST)
        if instruction_form.is_valid():
            # Cleaned data
            instruction_text = instruction_form.cleaned_data["instructions"]

            # Store in session
            data = {
                "instructions": instruction_text,
                "testator_id": str(userprofile.id),
            }
            request.session["pending_instruction"] = data

            # Generate token and verification link
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_instruction", kwargs={"token": token})
            )

            # Generate PDF
            pdf = generate_post_death_pdf(data, userprofile.full_name)

            # Send email
            email = EmailMessage(
                subject="Verify Post-Death Instruction",
                body=f"You submitted post-death instructions. "
                    f"Please confirm this action by clicking the link below:\n\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach("post_death_instructions.pdf", pdf.getvalue(), "application/pdf")
            email.send()

            messages.info(request, "A confirmation email has been sent. Please verify to finalize submission.")
            return redirect("administration:digitalwill")

        messages.error(request, "Please correct the errors in your form.")
        return redirect("administration:digitalwill")
    
    if request.method == "POST" and "add_audio_btn" in request.POST:
        audio_form = AudioInstructionForm(request.POST, request.FILES)
        if audio_form.is_valid():
            uploaded_audio = request.FILES.get("audio_file")
            if not uploaded_audio:
                messages.error(request, "No audio file uploaded.")
                return redirect("administration:digitalwill")

            # Store in session (audio content encoded as Latin-1)
            request.session["pending_audio"] = {
                "testator_id": str(userprofile.id),
                "filename": uploaded_audio.name,
                "content_type": uploaded_audio.content_type,
                "file_content": uploaded_audio.read().decode('latin1'),
            }

            # Create verification token
            token = signer.sign(str(uuid.uuid4()))
            verification_url = request.build_absolute_uri(
                reverse("administration:verify_audio", kwargs={"token": token})
            )

            # Send verification email
            email = EmailMessage(
                subject="Verify Audio Instruction Upload",
                body=f"You submitted an audio file. Please confirm by clicking:\n\n{verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.send()

            messages.info(request, "A verification email was sent. Please confirm to complete upload.")
            return redirect("administration:digitalwill")

        messages.error(request, "Please correct the form errors.")
        return redirect("administration:digitalwill")

    # if request.method == "POST" and "add_audio_instruction_btn" in request.POST:
    #     audio_instruction_form = AudioInstructionForm(request.POST or None, request.FILES or None)
    #     if audio_instruction_form.is_valid():
    #         # if Asset.objects.filter(full_name = request.POST.get("full_name")).exists():
    #         #    messages.info(request, f"Heir is already exists")
    #         #    return redirect("administration:digitalwill")
            
    #         audio_instruction_form_instance = audio_instruction_form.save(commit=False)
    #         audio_instruction_form_instance.testator = userprofile
    #         audio_instruction_form_instance.save()
    #         messages.success(request, f"Audio instruction was added successfully!")
    #         return redirect("administration:digitalwill")
            
    #     messages.error(request, f"Something went wrong, invalid credential!")
    #     return redirect("administration:digitalwill")
    
    special_account_form = SpecialAccountForm()
    confidential_info_form = ConfidentialInfoForm()
    executor_form = ExecutorForm()
    post_death_instruction_form = PostDeathInstructionForm()
    audio_instruction_form = AudioInstructionForm()
    asset_form = AssetForm()
    asset_form_instance = AssetForm(instance = asset_instance) 
    her_form = HeirForm()
    templates = "administration/digital_will.html"
    context = {
        "special_account_form":special_account_form,
        "confidential_info_form":confidential_info_form,
        "executor_form":executor_form,
        "post_death_instruction_form":post_death_instruction_form,
        "audio_instruction_form":audio_instruction_form,
        "her_form":her_form,
        "heirs":heirs,
        "asset_form":asset_form,
        "asset_form_instance":asset_form_instance,

        "assets":assets,
        "special_accounts":special_accounts,
        "confidential_infos":confidential_infos,
        "executors":executors,
        "post_death_instructions":post_death_instructions,
        "audio_instructions":audio_instructions
    }
    return render(request, templates, context)

def digitalwillUpdateHeirview(request, heir_id):
    if request.method == "POST" and "update_heir_btn" in request.POST:
        heir = Heir.objects.filter(id = heir_id).first()
        # testator
        heir.full_name = request.POST.get("full_name")
        heir.relationship = request.POST.get("relationship")
        heir.date_of_birth = request.POST.get("date_of_birth")
        heir.phone_number = request.POST.get("phone_number")  
        heir.save()
        messages.success(request, f"Heir information was updated successfully!")
        return redirect("administration:digitalwill")            

def digitalwillDeleteHeirview(request, heir_id):
    if request.method == "POST" and "delete_heir_btn" in request.POST:
        heir = Heir.objects.filter(id = heir_id).first()
        heir.delete()
        messages.success(request, f"Heir information was deleted successfully!")
        return redirect("administration:digitalwill")
    
def digitalwillUpdateAssetview(request, asset_id):
    if request.method == "POST" and "update_asset_btn" in request.POST:
        testator = UserProfile.objects.filter(user = request.user).first()
        asset = Asset.objects.filter(id = asset_id).first()
        asset_form = AssetForm(request.POST or None, request.FILES or None, instance = asset)
        if asset_form.is_valid():
            asset_form_instance = asset_form.save(commit=False)
            asset_form_instance.testator = testator
            asset_form_instance.asset_type = request.POST.get("asset_type")
            asset_form_instance.location = request.POST.get("location")
            asset_form_instance.estimated_value = request.POST.get("estimated_value")
            asset_form_instance.asset_image = request.POST.get("asset_image")
            asset_form_instance.instruction = request.POST.get("instruction")

            asset_form_instance.save()
            messages.success(request, f"Asset information was updated successfully!")
            return redirect("administration:digitalwill")

def digitalwillDeleteAssetview(request, asset_id):
    if request.method == "POST" and "delete_asset_btn" in request.POST:
        heir = Asset.objects.filter(id = asset_id).first()
        heir.delete()
        messages.success(request, f"Asset information was deleted successfully!")
        return redirect("administration:digitalwill")
