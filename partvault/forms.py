from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Collection, Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["user_code"]
        widgets = {
            "user_code": forms.TextInput(attrs={"maxlength": 3}),
        }

    def clean_user_code(self):
        user_code = self.cleaned_data["user_code"].strip().upper()
        if not user_code.isalnum():
            raise ValidationError("User code must be alphanumeric.")
        if (
            Profile.objects.filter(user_code=user_code)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("User code is already in use.")
        return user_code


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "collection_code", "is_public"]

    def clean_collection_code(self):
        collection_code = self.cleaned_data["collection_code"].strip().upper()
        if not collection_code.isalnum():
            raise ValidationError("Collection code must be alphanumeric.")
        return collection_code


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]


class SignupForm(UserCreationForm):
    user_code = forms.CharField(
        max_length=3,
        help_text=Profile._meta.get_field("user_code").help_text,
    )
    invitation_code = forms.CharField(
        max_length=120,
        help_text="Required. You can only sign up if you have received an invitation code.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            [
                "invitation_code",
                "username",
                "first_name",
                "last_name",
                "email",
                "user_code",
                "password1",
                "password2",
            ]
        )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "user_code",
            "invitation_code",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(user=user, user_code=self.cleaned_data["user_code"])
        return user

    def clean_user_code(self):
        user_code = self.cleaned_data["user_code"].strip().upper()
        if not user_code.isalnum():
            raise ValidationError("User code must be alphanumeric.")
        if Profile.objects.filter(user_code=user_code).exists():
            raise ValidationError("User code is already in use.")
        return user_code

    def clean_invitation_code(self):
        invitation_code = self.cleaned_data["invitation_code"].strip()
        if invitation_code.lower() != settings.INVITATION_CODE.lower():
            raise ValidationError("Invitation code is invalid.")
        return invitation_code
