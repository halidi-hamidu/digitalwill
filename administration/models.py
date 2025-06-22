from django.db import models
import uuid
from authentication.models import *

class RelationshipChoices(models.TextChoices):
    SPOUSE = 'Spouse', 'Spouse'
    CHILD = 'Child', 'Child'
    PARENT = 'Parent', 'Parent'
    SIBLING = 'Sibling', 'Sibling'
    OTHER = 'Other', 'Other'

class Heir(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='heirs')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    relationship = relationship = models.CharField(
    max_length=100,
    choices=RelationshipChoices.choices,
    default=RelationshipChoices.OTHER
    ) 
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Heir"
        verbose_name_plural = "Heirs"

    def __str__(self):
        return f"{self.full_name} ({self.relationship})"

# 3. Assets
class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='assets')
    asset_type = models.CharField(max_length=100, blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    asset_image = models.ImageField(upload_to="asset_images/", blank=True, null=True)
    instruction = models.TextField(blank=True, null=True)
    assigned_to = models.ManyToManyField(Heir, blank=True, null=True, related_name='inherited_assets')

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return f"{self.asset_type} - {self.location}"

# 4. Business or Special Accounts
class SpecialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='special_accounts', blank=True, null=True)
    account_type = models.CharField(max_length=100, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=255, blank=True, null=True)
    assigned_to = models.ForeignKey(Heir, on_delete=models.SET_NULL, blank=True, null=True, related_name='special_accounts')

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "SpecialAccount"
        verbose_name_plural = "SpecialAccounts"

    def __str__(self):
        return f"{self.account_type} - {self.account_name}"

# 5. Confidential Information
class ConfidentialInfo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='confidential_infos')
    confidential_file = models.FileField(blank=True, null=True, upload_to="confidential_files/")
    instructions = models.TextField()
    assigned_to = models.ForeignKey(Heir, on_delete=models.SET_NULL, blank=True, null=True, related_name='confidential_access')

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "ConfidentialInfo"
        verbose_name_plural = "ConfidentialInfo"

    def __str__(self):
        return f"{self.account_type} for {self.email_or_username}"

# 6. Executor
class Executor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='executor')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Executor"
        verbose_name_plural = "Executors"

    def __str__(self):
        return self.full_name

# 7. Post-Death Instructions
class PostDeathInstruction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='post_death_instruction')
    instructions = models.TextField()

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "PostDeathInstruction"
        verbose_name_plural = "PostDeathInstructions"

    def __str__(self):
        return f"Instructions for {self.testator.full_name}"

# 8. Audio Upload
class AudioInstruction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    testator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='audio_instructions')
    audio_file = models.FileField(upload_to='audio_wills/')

    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "AudioInstruction"
        verbose_name_plural = "AudioInstruction"

    def __str__(self):
        return f"Audio by {self.testator.full_name}"
