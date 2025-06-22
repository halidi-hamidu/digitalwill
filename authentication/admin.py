from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(UserProfile)
class UserProfileModel(admin.ModelAdmin):
    list_display = ("id","full_name","gender","date_of_birth","phone_number","email","nida_number","address","roles")
    display_filter = ("id","full_name","gender","date_of_birth","phone_number","email","nida_number","address","roles")
