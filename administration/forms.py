from django import forms
from .models import *

class HeirForm(forms.ModelForm):
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = Heir
        fields = "__all__"
        exclude = ["testator"]

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = "__all__"
        exclude = ["testator"]

class SpecialAccountForm(forms.ModelForm):
    class Meta:
        model = SpecialAccount
        fields = "__all__"
        exclude = ["testator", "Heir"]

class ConfidentialInfoForm(forms.ModelForm):
    class Meta:
        model = ConfidentialInfo
        fields = "__all__"
        exclude = ["testator"]

class ExecutorForm(forms.ModelForm):
    class Meta:
        model = Executor
        fields = "__all__"
        exclude = ["testator"]

class PostDeathInstructionForm(forms.ModelForm):
    class Meta:
        model = PostDeathInstruction
        fields = "__all__"
        exclude = ["testator"]

class AudioInstructionForm(forms.ModelForm):
    class Meta:
        model = AudioInstruction
        fields = ["audio_file"]
        exclude = ["testator"]

    def clean_audio_file(self):
        file = self.cleaned_data.get("audio_file")
        if file:
            if file.size > 10 * 1024 * 1024:  # 10 MB limit
                raise forms.ValidationError("Audio file too large (max 10MB).")
        return file