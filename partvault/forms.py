from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class ProfileForm(forms.ModelForm):
    asset_tag_prefix = forms.CharField(max_length=3, help_text="Required.")

    class Meta:
        model = Profile
        fields = ["asset_tag_prefix"]
        widgets = {
            "asset_tag_prefix": forms.TextInput(attrs={"maxlength": 3}),
        }

    def clean_asset_tag_prefix(self):
        asset_tag_prefix = self.cleaned_data["asset_tag_prefix"].strip().upper()
        if not asset_tag_prefix.isalnum():
            raise ValidationError("Asset tag prefix must be alphanumeric.")
        if (
            Profile.objects.filter(asset_tag_prefix=asset_tag_prefix)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("Asset tag prefix is already in use.")
        return asset_tag_prefix


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]


class SignupForm(UserCreationForm):
    asset_tag_prefix = forms.CharField(
        max_length=3,
        help_text="Required. 1 to 3 alphanumeric characters that will be used as a user asset tag prefix for all items you create. Items belong to a collection, which also has a prefix, user and collection prefixes will be concatenated.",
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
                "asset_tag_prefix",
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
            "asset_tag_prefix",
            "invitation_code",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(
                user=user, asset_tag_prefix=self.cleaned_data["asset_tag_prefix"]
            )
        return user

    def clean_asset_tag_prefix(self):
        asset_tag_prefix = self.cleaned_data["asset_tag_prefix"].strip().upper()
        if not asset_tag_prefix.isalnum():
            raise ValidationError("Asset tag prefix must be alphanumeric.")
        if Profile.objects.filter(asset_tag_prefix=asset_tag_prefix).exists():
            raise ValidationError("Asset tag prefix is already in use.")
        return asset_tag_prefix

    def clean_invitation_code(self):
        invitation_code = self.cleaned_data["invitation_code"].strip()
        if invitation_code.lower() != settings.INVITATION_CODE.lower():
            raise ValidationError("Invitation code is invalid.")
        return invitation_code
