from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from .models import *
from .forms import *
from django.db.models import Q
from django.contrib import messages
from administration.models import *
from administration.forms import *
from django.contrib.auth.models import User
from django.conf import settings
# email support models
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.encoding import force_str
import uuid
import json
from utils import generate_pdf_from_template
from django.core.mail import EmailMessage
from io import BytesIO
from reportlab.pdfgen import canvas
from django.core.signing import Signer, BadSignature
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.views.decorators.cache import cache_control

# views.py

signer = TimestampSigner()
VERIFICATION_EXPIRATION_SECONDS = 60 * 60 * 24  # 1 day

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_email_view(request, token):
    try:
        email = signer.unsign(token, max_age=VERIFICATION_EXPIRATION_SECONDS)
        userprofile = get_object_or_404(UserProfile, user__email=email)
        userprofile.email_verified = True
        userprofile.save()
        messages.success(request, "Email verified successfully! You can now update your profile.")
    except SignatureExpired:
        messages.error(request, "Verification link expired. Please request a new verification email.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")

    return redirect("authentication:personalinformation")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def resend_verification_email(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    user = request.user

    if userprofile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("authentication:personalinformation")

    token = signer.sign(user.email)
    verification_url = request.build_absolute_uri(
        reverse("authentication:verify_email", kwargs={"token": token})
    )
    pdf_buffer = generate_user_pdf(user, userprofile)

    email = EmailMessage(
        subject="Verify your email address",
        body=f"Please verify your email by clicking the link below:\n{verification_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach("user_profile.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()

    messages.success(request, "Verification email resent successfully.")
    return redirect("authentication:personalinformation")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    userprofile = UserProfile.objects.filter(user = user).first()
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse("Email verified! You can now log in.")
    else:
        return HttpResponse("Verification link is invalid or expired.")

# Create your views here.
def loginview(request):
    if request.method == "POST" and "login_user_btn" in request.POST:
        authenticated_user = authenticate(username = request.POST.get("username"), password = request.POST.get("password"))
        if authenticated_user is not None:
            login(request, authenticated_user)
            messages.success(request, f"Login successful, welcome {request.POST.get("username")}")
            return redirect("administration:dashboard")
        messages.success(request, f"User does not exist, try again")
        return redirect("authentication:auth")
    login_form = AuthenticationForm()
    templates = "authentication/login.html"
    context = {
        "login_form":login_form
    }
    return render(request, templates, context)

def registerview(request):
    if request.method == "POST" and "register_user_btn" in request.POST:
        register_form = UserCreationForm(request.POST or None)
        if register_form.is_valid():
            if not User.objects.filter(username = request.POST.get("username"), password = request.POST.get("password1")).exists():
                register_instance = register_form.save(commit=False)
                register_instance.email = request.POST.get("username")
                register_instance.is_active = False
                userprofile = UserProfile(
                    user = register_instance,
                    email = register_instance.email
                )
                token = default_token_generator.make_token(register_instance)
                uid = urlsafe_base64_encode(force_bytes(register_instance.pk))
                domain = get_current_site(request).domain
                verification_link = f"http://{domain}{reverse('authentication:verify-email', kwargs={'uidb64': uid, 'token': token})}"

                # Send verification email
                subject = "Verify your email"
                message = render_to_string('authentication/accounts/verify_email.html', {
                    'user': register_instance.username,
                    'verification_link': verification_link,
                })
                message_from = settings.EMAIL_HOST_USER

                print(f"####################")
                print(f"Subject: {subject}")
                print(f"Message: {message}")
                print(f"From: {message_from}")
                print(f"To: {[register_instance.email]}")
                print(f"####################")
    
                send_mail(subject, message, message_from, [register_instance.email])
                if send_mail(subject, message, message_from, [register_instance.email]):
                    print("Email sent successfully!")
                else:
                    print("Failed sent an email successfully!")
                
                userprofile.email_verified = True
                userprofile.is_active = True
                register_instance.save()
                userprofile.save()
                # return HttpResponse("Please check your email to verify your account.")
                messages.success(request, f"Please check your email to verify your account.!")
                return redirect("authentication:registration")
            messages.info(request, f"User {request.POST.get("username")} is already exists")
            return redirect("authentication:registration")
        messages.error(request, f"Something went wrong, invalid credentials")
        return redirect("authentication:registration")

    register_form = UserCreationForm()
    templates = "authentication/register.html"
    context = {
        "register_form":register_form
    }
    return render(request, templates, context)


signer = Signer()
@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def generate_user_pdf(user, profile):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, "User Profile Details")
    p.drawString(100, 780, f"Full Name: {profile.full_name}")
    p.drawString(100, 760, f"Email: {user.email}")
    p.drawString(100, 740, f"Gender: {profile.gender}")
    p.drawString(100, 720, f"Date of Birth: {profile.date_of_birth}")
    p.drawString(100, 700, f"Phone: {profile.phone_number}")
    p.drawString(100, 680, f"NIDA Number: {profile.nida_number}")
    p.drawString(100, 660, f"Address: {profile.address}")
    p.drawString(100, 640, f"Role: {profile.roles}")
    p.drawString(100, 620, f"Email Verified: {profile.email_verified}")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def personalinformationview(request):
    userprofile_instance = get_object_or_404(UserProfile, user=request.user)
    user_instance = request.user

    if request.method == "POST" and "update_user_profile_btn" in request.POST:
        userprofile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile_instance)
        userform = UserForm(request.POST, instance=user_instance)

        if userprofile_form.is_valid() and userform.is_valid():
            if not userprofile_instance.email_verified:
                # Generate verification token
                token = signer.sign(user_instance.email)
                verification_url = request.build_absolute_uri(
                    reverse("authentication:verify_email", kwargs={"token": token})
                )

                # Generate PDF
                pdf_buffer = generate_user_pdf(user_instance, userprofile_instance)

                # Compose and send email
                email = EmailMessage(
                    subject="Verify your email address",
                    body=f"Please verify your email by clicking the link below:\n{verification_url}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user_instance.email],
                )
                email.attach("user_profile.pdf", pdf_buffer.getvalue(), "application/pdf")
                email.send()

                messages.info(request, "Verification link and PDF profile have been sent to your email.")
                return redirect("authentication:personalinformation")

            # Save changes only if email is verified
            userform_instance = userform.save(commit=False)
            userprofile_form_instance = userprofile_form.save(commit=False)

            if UserProfile.objects.filter(nida_number=request.POST.get("nida_number"))\
                                  .exclude(pk=userprofile_instance.pk).exists():
                messages.info(request, f"NIDA number {request.POST.get('nida_number')} is already in use.")
                return redirect("authentication:personalinformation")

            userform_instance.save()
            userprofile_form_instance.user = user_instance
            userprofile_form_instance.full_name = f"{userform_instance.first_name} {userform_instance.last_name}"
            userprofile_form_instance.email = user_instance.email
            userprofile_form_instance.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("authentication:personalinformation")

        messages.error(request, "Something went wrong. Please check the form.")
        return redirect("authentication:personalinformation")

    userprofile_form = UserProfileForm(instance=userprofile_instance)
    userform = UserForm(instance=user_instance)

    return render(request, "authentication/personal_information.html", {
        "userprofile_form": userprofile_form,
        "userprofile": userprofile_instance,
        "userform": userform,
    })

signer = Signer()  # You can use TimestampSigner if you want expiration support

def verify_email_view(request, token):
    try:
        # Step 1: Decode token (raises BadSignature if invalid)
        email = signer.unsign(token)
        
        # Step 2: Find user
        user = get_object_or_404(User, email=email)
        userprofile = get_object_or_404(UserProfile, user=user)

        # Step 3: Check and update email_verified
        if userprofile.email_verified:
            messages.info(request, "Your email is already verified.")
        else:
            userprofile.email_verified = True
            userprofile.save()
            messages.success(request, "Email verification successful!")

    except BadSignature:
        messages.error(request, "Invalid or tampered verification link.")
    except User.DoesNotExist:
        messages.error(request, "No user found with this email.")
    except UserProfile.DoesNotExist:
        messages.error(request, "No user profile associated with this user.")

    return redirect("authentication:personalinformation")

def logoutview(request):
    if request.method == "POST" and "logout_user_btn" in request.POST:
        logout(request)
        return redirect("authentication:auth")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def accountsettingview(request):
    user_accounts = get_user_model().objects.all().order_by("-id")
    templates = "authentication/account_setting.html"
    context = {
        "user_accounts":user_accounts
    }
    return render(request, templates, context)

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def deleteuseraccountview(request, user_id):
    if request.method == "POST" and "delete_user_account_btn" in request.POST:
        user_account = get_object_or_404(User, pk = user_id)
        user_account.delete()
        messages.success(request, f"User deleted successfully")
        return redirect("authentication:accountsetting")

@cache_control(no_cache=True, must_revalidate=True, no_store=True, private=True)
@login_required
def updateuseraccountview(request, user_id):
    if request.method == "POST" and "update_user_account_btn" in request.POST:
        get_user = get_object_or_404(User, pk=user_id)
        userprofile_instance = UserProfile.objects.filter(user=get_user).first()

        # Update User model fields
        get_user.first_name = request.POST.get("first_name", "")
        get_user.last_name = request.POST.get("last_name", "")
        get_user.email = request.POST.get("email", "")
        get_user.username = get_user.email  # Use email as username

        # Update UserProfile fields
        if userprofile_instance:
            userprofile_instance.full_name = f"{get_user.first_name} {get_user.last_name}"
            userprofile_instance.gender = request.POST.get("gender", "")
            userprofile_instance.address = request.POST.get("address", "")
            # userprofile_instance.roles = request.POST.get("roles", "")
            if request.POST.get("roles", "") == "Admin":
                userprofile_instance.roles = "Admin"
                get_user.is_superuser = True
            else:
                userprofile_instance.roles = "Testator"
                get_user.is_superuser = False

            userprofile_instance.phone_number = request.POST.get("phone_number", "")
            userprofile_instance.email = get_user.email

            dob = request.POST.get("date_of_birth")
            if dob:
                userprofile_instance.date_of_birth = dob

            # Handle NIDA uniqueness check
            new_nida = request.POST.get("nida_number", "")
            if new_nida:
                # Check if the NIDA is already taken by another user
                if UserProfile.objects.filter(Q(nida_number=new_nida) & ~Q(user=get_user)).exists():
                    messages.error(request, "Sorry, this NIDA number is already taken.")
                    return redirect("authentication:accountsetting")

                userprofile_instance.nida_number = new_nida

        # Save updates
        get_user.save()
        if userprofile_instance:
            userprofile_instance.save()

        messages.success(request, "User account was updated successfully!")
        return redirect("authentication:accountsetting")

    return redirect("authentication:accountsetting")
           