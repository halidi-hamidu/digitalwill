from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(Heir)
class HeirModel(admin.ModelAdmin):
    list_display = ("id","full_name","relationship","date_of_birth","phone_number")
    display_filter = ("id","full_name","relationship","date_of_birth","phone_number")

@admin.register(Asset)
class AssetModel(admin.ModelAdmin):
    list_display = ("id","asset_type","location","estimated_value")
    display_filter = ("id","asset_type","location","estimated_value")

@admin.register(SpecialAccount)
class SpecialAccountModel(admin.ModelAdmin):
    list_display = ("id","account_type","account_name","account_number")
    display_filter = ("id","account_type","account_name","account_number")

@admin.register(ConfidentialInfo)
class ConfidentialInfoModel(admin.ModelAdmin):
    list_display = ("id","confidential_file","instructions")
    display_filter = ("id","confidential_file","instructions")

@admin.register(Executor)
class ExecutorModel(admin.ModelAdmin):
    list_display = ("id","full_name","relationship","phone_number")
    display_filter = ("id","full_name","relationship","phone_number")

@admin.register(PostDeathInstruction)
class PostDeathInstructionModel(admin.ModelAdmin):
    list_display = ("id","instructions")
    display_filter = ("id","instructions")

@admin.register(AudioInstruction)
class AudioInstructionModel(admin.ModelAdmin):
    list_display = ("id","audio_file")
    display_filter = ("id","audio_file")
