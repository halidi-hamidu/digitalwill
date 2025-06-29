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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.utils import timezone

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

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from django.core.mail import EmailMessage
from django.conf import settings
from utils import generate_updated_user_pdf

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
            messages.error(request, "Invalid registration. Please check the form.")
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
            messages.info(request, "Email is already verified.")
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
        messages.info(request, f"User does not exist, try again")
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
# Register Montserrat fonts (ensure .ttf files are in your project folder)
pdfmetrics.registerFont(TTFont("Montserrat-Bold", "Montserrat-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Montserrat-Thin", "Montserrat-VariableFont_wght.ttf"))

def generate_user_pdf(user, profile):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    current_date = datetime.now().strftime("%d %B %Y")

    # ------------------- TOP CONTENT -------------------
    p.setFont("Montserrat-Bold", 20)
    p.setFillColor(colors.orange)
    p.drawString(50, height - 50, "🧾 Seduta Will")

    p.setFont("Montserrat-Bold", 12)
    p.setFillColor(colors.black)
    p.drawRightString(width - 50, height - 45, current_date)

    p.setStrokeColor(colors.orange)
    p.setLineWidth(1.5)
    p.line(50, height - 60, width - 50, height - 60)

    # ------------------- MIDDLE CONTENT -------------------
    p.setFont("Montserrat-Bold", 16)
    p.setFillColor(colors.orange)
    p.drawString(50, height - 90, "User Details")  # LEFT-aligned now

    data = [
        ["Full Name", profile.full_name],
        ["Email", user.email],
        ["Gender", profile.gender],
        ["Date of Birth", str(profile.date_of_birth)],
        ["Phone", profile.phone_number],
        ["NIDA Number", profile.nida_number],
        ["Address", profile.address],
        # ["Role", ", ".join(profile.roles) if isinstance(profile.roles, list) else profile.roles],
    ]

    # Full-width table (minus margins)
    margin = 50
    table_width = width - 2 * margin
    col_widths = [table_width * 0.3, table_width * 0.7]

    table = Table(data, colWidths=col_widths)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Montserrat-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ])
    table.setStyle(style)

    table_top = height - 110
    table_height = len(data) * 18
    table.wrapOn(p, width, height)
    table.drawOn(p, margin, table_top - table_height)

    # ------------------- DECLARATION -------------------
    declaration_paragraphs = [
        "I confirm that the information provided above is true, complete, and correct to the best of my knowledge. This profile accurately reflects my current personal, professional, and legal status as recognized by relevant authorities.",
        
        "The contents of this document are based on verified data submitted and authorized for digital documentation. I acknowledge that any false or misleading information may result in legal implications under applicable laws and regulations.",
        
        "This digital profile has been prepared for official use and may be presented as supporting evidence for identity verification, administrative processes, and other formal engagements requiring proof of personal data.",
        
        "I understand and accept that Seduta Will, as the issuing authority, maintains the right to store, audit, and validate this information in line with its data governance policies and the legal framework of Tanzania."
    ]

    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        name='Justified',
        parent=styles['Normal'],
        fontName="Montserrat-Bold",
        fontSize=11,
        leading=14,
        alignment=4,  # Justified
    )

    decl_start_y = table_top - table_height - 40
    for paragraph in declaration_paragraphs:
        para = Paragraph(paragraph, para_style)
        para_width, para_height = para.wrap(width - 2 * margin, height)
        para.drawOn(p, margin, decl_start_y - para_height)
        decl_start_y -= para_height + 10  # Spacing between paragraphs

    # ------------------- FOOTER CONTENT -------------------
    footer_y = 80
    line_spacing = 16

    p.setStrokeColor(colors.orange)
    p.setLineWidth(0.5)
    p.line(margin, footer_y + 26, width - margin, footer_y + 26)

    p.setFont("Montserrat-Bold", 10)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, footer_y + (line_spacing * 2), f"PDF ID: {user.id}-{profile.id}")
    p.drawCentredString(width / 2, footer_y + line_spacing, "Seduta Will, P.O. Box 15777, Kawe, Dar es Salaam")

    p.setFillColor(colors.orange)
    p.drawCentredString(width / 2, footer_y, "ISO 1496177")

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

signer = signing.TimestampSigner()
@cache_control(no_cache=True, privacy=True, must_revalidate=True, no_store=True)
@login_required
def personalinformationview(request):
    get_current_year = timezone.now
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
        "user_instance":user_instance,
        "get_current_year":get_current_year
    })


# def verify_email(request, token):
#     try:
#         # max_age=86400 seconds = 1 day expiry
#         data = signing.loads(token, max_age=86400)
#         user = User.objects.get(pk=data["user_pk"])
#         form_data = data["form_data"]

#         # Convert ISO string dates back to date objects
#         date_fields = ['date_of_birth', 'created_at', 'updated_at']  # add any other date fields here

#         for field in date_fields:
#             if field in form_data and form_data[field]:
#                 try:
#                     form_data[field] = datetime.fromisoformat(form_data[field]).date()
#                 except ValueError:
#                     form_data[field] = None

#         profile = UserProfile.objects.get(user=user)

#         # Check uniqueness before applying updates
#         if UserProfile.objects.filter(nida_number=form_data.get("nida_number"))\
#                               .exclude(pk=profile.pk).exists():
#             messages.error(request, f"NIDA number {form_data.get('nida_number')} is already in use.")
#             return redirect("authentication:personalinformation")
        
#         if UserProfile.objects.filter(phone_number=form_data.get("phone_number"))\
#                               .exclude(pk=profile.pk).exists():
#             messages.error(request, f"Phone number {form_data.get('phone_number')} is already in use.")
#             return redirect("authentication:personalinformation")

#         if User.objects.filter(username=form_data.get('username'))\
#                               .exclude(pk=user.pk).exists():
#             messages.error(request, f"Username {form_data.get('username')} is already in use.")
#             return redirect("authentication:personalinformation")

#         # Update User fields
#         user.first_name = form_data.get("first_name", user.first_name)
#         user.last_name = form_data.get("last_name", user.last_name)
#         user.username = form_data.get("username", user.username)
#         user.email = form_data.get("username", user.email)
#         user.save()

#         # Update UserProfile fields
#         for field, value in form_data.items():
#             if field in ["user", "email_verified", "is_active"]:
#                 continue
#             if hasattr(profile, field):
#                 setattr(profile, field, value)

#         profile.email_verified = True
#         profile.is_active = True
#         profile.save()

#         messages.success(request, "Email verified and profile updated successfully.")
#         return redirect("authentication:personalinformation")

#     except User.DoesNotExist:
#         messages.error(request, "Invalid user.")
#     except UserProfile.DoesNotExist:
#         messages.error(request, "User profile not found.")
#     except SignatureExpired:
#         messages.error(request, "Verification link expired.")
#     except BadSignature:
#         messages.error(request, "Invalid verification link.")
#     except Exception as e:
#         messages.error(request, f"An error occurred: {e}")

#     return redirect("authentication:personalinformation")

def verify_email(request, token):
    try:
        data = signing.loads(token, max_age=86400)
        user = User.objects.get(pk=data["user_pk"])
        form_data = data["form_data"]

        # -- Convert ISO-dates --
        for field in ['date_of_birth', 'created_at', 'updated_at']:
            if form_data.get(field):
                try:
                    form_data[field] = datetime.fromisoformat(form_data[field]).date()
                except ValueError:
                    form_data[field] = None

        profile = UserProfile.objects.get(user=user)

        # -- Uniqueness checks --
        if UserProfile.objects.filter(nida_number=form_data.get("nida_number")).exclude(pk=profile.pk).exists():
            messages.error(request, f"NIDA number {form_data['nida_number']} is already in use.")
            return redirect("authentication:personalinformation")
        if UserProfile.objects.filter(phone_number=form_data.get("phone_number")).exclude(pk=profile.pk).exists():
            messages.error(request, f"Phone number {form_data['phone_number']} is already in use.")
            return redirect("authentication:personalinformation")
        if User.objects.filter(username=form_data.get("username")).exclude(pk=user.pk).exists():
            messages.error(request, f"Username {form_data['username']} is already in use.")
            return redirect("authentication:personalinformation")

        # -- Update User --
        user.first_name = form_data.get("first_name", user.first_name)
        user.last_name = form_data.get("last_name", user.last_name)
        user.username = form_data.get("username", user.username)
        user.email = form_data.get("username", user.email)
        user.save()

        # -- Update Profile --
        for field, val in form_data.items():
            if field in ["user", "email_verified", "is_active"]:
                continue
            if hasattr(profile, field):
                setattr(profile, field, val)

        profile.email_verified = True
        profile.is_active = True
        profile.save()

        # -- Generate & Send PDF if Approved --
        pdf_buffer = generate_updated_user_pdf(user, profile)

        # --- Email to current user ---
        user_email = EmailMessage(
            subject="Your Profile on Seduta Will — Approved",
            body=(
                f"Hello {user.get_full_name()},\n\n"
                "Congratulations! Your profile has been verified and officially approved.\n"
                "Please find an attached PDF summary of your updated details.\n\n"
                "Thank you for being with Seduta Will.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        user_email.attach("profile_update.pdf", pdf_buffer.getvalue(), "application/pdf")
        user_email.send(fail_silently=False)

        # --- Email to admins ---
        admin_emails = list(
            User.objects.filter(user_userprofile__roles="Admin")
                        .values_list("email", flat=True)
        )
        if admin_emails:
            admin_email = EmailMessage(
                subject=f"User Approved: {user.get_full_name()}",
                body=(
                    f"Dear Admin,\n\n"
                    f"User {user.get_full_name()} ({user.email}) has verified their email and been marked as *APPROVED*.\n"
                    "Attached is their updated profile summary.\n\n"
                    "— Seduta Will System"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails,
            )
            admin_email.attach("approved_user_profile.pdf", pdf_buffer.getvalue(), "application/pdf")
            admin_email.send(fail_silently=False)

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
        messages.error(request, f"An unexpected error occurred: {e}")

    return redirect("authentication:personalinformation")

@cache_control(no_cache = True, privacy = True, must_revalidate = True, no_store = True)
@login_required
def accountsettingview(request):
    get_current_year = timezone.now
    user_accounts = get_user_model().objects.all().order_by("-id")
    templates = "authentication/account_setting.html"
    context = {
        "user_accounts":user_accounts,
        "get_current_year":get_current_year
        # "userprofileform":userprofileform
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
            print(f"################################")
            print(f"{request.POST.get("updateuseraccount")}")
            if not request.POST.get("manageuseraccount") == "on":
                userprofile_instance.manageuseraccount = False
            else:
                userprofile_instance.manageuseraccount = True

            if not request.POST.get("updateuseraccount") == "on":
                userprofile_instance.updateuseraccount = False
            else:
                userprofile_instance.updateuseraccount = True
            
            if not request.POST.get("viewuseraccount") == "on":
                userprofile_instance.viewuseraccount = False
            else:
                userprofile_instance.viewuseraccount = True

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