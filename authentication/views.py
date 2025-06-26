from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from datetime import date, datetime
from .models import *
from django.core import signing
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

from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class CustomPasswordResetView(PasswordResetView):
    template_name = 'authentication/registration/password_reset_form.html'
    email_template_name = 'authentication/registration/password_reset_email.html'
    subject_template_name = 'authentication/registration/password_reset_subject.txt'
    success_url = reverse_lazy('authentication:password_reset_done')
    token_generator = default_token_generator

    def form_valid(self, form):
        """Send the password reset email manually with full context."""
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'request': self.request,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
        }

        for user in form.get_users(form.cleaned_data["email"]):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = self.token_generator.make_token(user)
            password_reset_confirm_url = self.request.build_absolute_uri(
                reverse('authentication:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )

            context = {
                'email': user.email,
                'domain': self.request.get_host(),
                'site_name': 'localhost:8000',
                'uid': uid,
                'user': user,
                'token': token,
                'protocol': 'https' if self.request.is_secure() else 'http',
                'password_reset_confirm_url': password_reset_confirm_url,
            }

            subject = render_to_string(self.subject_template_name, context).strip()
            body = render_to_string(self.email_template_name, context)

            send_mail(subject, body, opts['from_email'], [user.email])

        return super().form_valid(form)

# views.py
def registerview(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["username"]  # assuming username is used as email
            if User.objects.filter(username=email).exists():
                messages.info(request, f"Email {email} is already in use.")
                return redirect("authentication:registration")

            # Create user and deactivate
            user = form.save(commit=False)
            user.email = email
            user.is_active = False
            user.save()

            # Create associated UserProfile
            UserProfile.objects.create(user=user, email=email, email_verified=False)

            # Generate verification token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = request.build_absolute_uri(
                reverse("authentication:verify_email", kwargs={"uidb64": uid, "token": token})
            )

            # Send verification email
            subject = "Verify your email address"
            body = render_to_string("authentication/accounts/verify_email.html", {
                "user": user.username,
                "verification_link": link,
            })
            email_message = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
            email_message.content_subtype = "html"  # Ensure HTML rendering
            email_message.send()

            messages.success(request, "Registration successful! Please check your email to verify.")
            return redirect("authentication:registration")
        else:
            messages.error(request, "❌ Invalid registration. Please check the form.")
            return redirect("authentication:registration")

    # GET request
    return render(request, "authentication/register.html", {"register_form": UserCreationForm()})


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and default_token_generator.check_token(user, token):
        profile = get_object_or_404(UserProfile, user=user)
        if not profile.email_verified:
            profile.email_verified = True
            user.is_active = True
            user.save()
            profile.save()
            messages.success(request, "Email verified successfully! You can now log in.")
        else:
            messages.info(request, "ℹEmail is already verified.")
    else:
        messages.error(request, "Invalid or expired verification link.")

    return redirect("authentication:registration")


signer = TimestampSigner()
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

def verify_failed(request):
    return render(request, "authentication/verify_failed.html")

signer = Signer()
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

signer = signing.TimestampSigner()

@cache_control(no_cache=True, privacy=True, must_revalidate=True, no_store=True)
@login_required
def personalinformationview(request):
    userprofile_instance = get_object_or_404(UserProfile, user=request.user)
    user_instance = request.user

    if request.method == "POST" and "update_user_profile_btn" in request.POST:
        userprofile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile_instance)
        userform = UserForm(request.POST, instance=user_instance)

        if userprofile_form.is_valid() and userform.is_valid():
            if not userprofile_instance.email_verified:
                # Combine form data and convert dates to strings
                form_data = {}
                form_data.update(userprofile_form.cleaned_data)
                form_data.update(userform.cleaned_data)

                # Remove file fields that cannot be serialized
                form_data.pop('profie_image', None)  # adjust if your field name differs

                # Convert date/datetime objects to ISO strings
                for key, value in form_data.items():
                    if isinstance(value, (date,)):
                        form_data[key] = value.isoformat()

                # Create signed token with user PK and form data
                token = signing.dumps({
                    "user_pk": user_instance.pk,
                    "form_data": form_data,
                })

                verification_url = request.build_absolute_uri(
                    reverse("authentication:verify_email", kwargs={"token": token})
                )

                # Generate PDF for current profile (not updated)
                pdf_buffer = generate_user_pdf(user_instance, userprofile_instance)

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

            # If already verified — update immediately
            if UserProfile.objects.filter(nida_number=request.POST.get("nida_number"))\
                                  .exclude(pk=userprofile_instance.pk).exists():
                messages.info(request, f"NIDA number {request.POST.get('nida_number')} is already in use.")
                return redirect("authentication:personalinformation")
            
            if UserProfile.objects.filter(phone_number=request.POST.get("phone_number"))\
                                  .exclude(pk=userprofile_instance.pk).exists():
                messages.info(request, f"Phone number {request.POST.get('phone_number')} is already in use.")
                return redirect("authentication:personalinformation")

            if User.objects.filter(username=request.POST.get('username'))\
                                  .exclude(pk=user_instance.pk).exists():
                messages.info(request, f"Username {request.POST.get('username')} is already in use.")
                return redirect("authentication:personalinformation")

            userform_instance = userform.save(commit=False)
            userprofile_form_instance = userprofile_form.save(commit=False)

            userform_instance.first_name = request.POST.get("first_name")
            userform_instance.last_name = request.POST.get("last_name")
            userform_instance.username = request.POST.get("username")
            userform_instance.email = request.POST.get("username")
            userform_instance.save()
            
            userprofile_form_instance.user = user_instance
            userprofile_form_instance.full_name = f"{userform_instance.first_name} {userform_instance.last_name}"
            userprofile_form_instance.email = userform_instance.email
            userprofile_form_instance.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("authentication:personalinformation")

        messages.error(request, "Something went wrong. Please check the form.")
        return redirect("authentication:personalinformation")

    # GET request
    userprofile_form = UserProfileForm(instance=userprofile_instance)
    userform = UserForm(instance=user_instance)

    return render(request, "authentication/personal_information.html", {
        "userprofile_form": userprofile_form,
        "userprofile": userprofile_instance,
        "userform": userform,
    })


def verify_email(request, token):
    try:
        # max_age=86400 seconds = 1 day expiry
        data = signing.loads(token, max_age=86400)
        user = User.objects.get(pk=data["user_pk"])
        form_data = data["form_data"]

        # Convert ISO string dates back to date objects
        date_fields = ['date_of_birth', 'created_at', 'updated_at']  # add any other date fields here

        for field in date_fields:
            if field in form_data and form_data[field]:
                try:
                    form_data[field] = datetime.fromisoformat(form_data[field]).date()
                except ValueError:
                    form_data[field] = None

        profile = UserProfile.objects.get(user=user)

        # Check uniqueness before applying updates
        if UserProfile.objects.filter(nida_number=form_data.get("nida_number"))\
                              .exclude(pk=profile.pk).exists():
            messages.error(request, f"NIDA number {form_data.get('nida_number')} is already in use.")
            return redirect("authentication:personalinformation")
        
        if UserProfile.objects.filter(phone_number=form_data.get("phone_number"))\
                              .exclude(pk=profile.pk).exists():
            messages.error(request, f"Phone number {form_data.get('phone_number')} is already in use.")
            return redirect("authentication:personalinformation")

        if User.objects.filter(username=form_data.get('username'))\
                              .exclude(pk=user.pk).exists():
            messages.error(request, f"Username {form_data.get('username')} is already in use.")
            return redirect("authentication:personalinformation")

        # Update User fields
        user.first_name = form_data.get("first_name", user.first_name)
        user.last_name = form_data.get("last_name", user.last_name)
        user.username = form_data.get("username", user.username)
        user.email = form_data.get("username", user.email)
        user.save()

        # Update UserProfile fields
        for field, value in form_data.items():
            if field in ["user", "email_verified", "is_active"]:
                continue
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.email_verified = True
        profile.is_active = True
        profile.save()

        messages.success(request, "Email verified and profile updated successfully.")
        return redirect("authentication:personalinformation")

    except User.DoesNotExist:
        messages.error(request, "Invalid user.")
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
    except SignatureExpired:
        messages.error(request, "Verification link expired.")
    except BadSignature:
        messages.error(request, "Invalid verification link.")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")

    return redirect("authentication:personalinformation")


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

def logoutview(request):
    if request.method == "POST" and "logout_user_btn" in request.POST:
        logout(request)
        return redirect("authentication:auth")