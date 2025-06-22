from django.db import models
import uuid
from django.contrib.auth.models import User, AbstractUser

# class CustomUser(AbstractUser):
#     email_verified = models.BooleanField(default=False)

class UserProfile(models.Model):
    ROLES = [
        ('Admin','Admin'),
        ('Testator','Testator'),
    ]

    GENDER = [
        ('Male','Male'),
        ('Female','Female'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_userprofile")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True, choices=GENDER, default="Male")
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    nida_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    roles = models.CharField(max_length=255, choices=ROLES, default="Testator", blank=True, null=True)
    profie_image = models.FileField(upload_to="userprofile/", blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    class Meta:
        verbose_name = "UserProfile"
        verbose_name_plural = "UserProfile"
    
    def __str__(self):
        return f"{self.full_name}"

class PendingUserProfileUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField()
    token = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Pending Update for {self.user.username}"
