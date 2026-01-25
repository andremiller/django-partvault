from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import (
    Category,
    Collection,
    Document,
    Item,
    Link,
    Manufacturer,
    Photo,
    Profile,
    Status,
    Tag,
)


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


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "collection",
            "name",
            "category",
            "manufacturer",
            "model",
            "revision",
            "serial",
            "status",
            "parent_item",
            "tags",
            "notes",
            "acquired_on",
            "last_tested_on",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
            "acquired_on": forms.DateInput(attrs={"type": "date"}),
            "last_tested_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, collection=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["collection"].queryset = Collection.objects.filter(owner=user)
        else:
            self.fields["collection"].queryset = Collection.objects.none()

        selected_collection = collection
        if self.is_bound:
            collection_id = self.data.get("collection")
            if collection_id:
                collection_filter = {"pk": collection_id}
                if user:
                    collection_filter["owner"] = user
                selected_collection = Collection.objects.filter(
                    **collection_filter
                ).first()
        elif self.instance and self.instance.collection_id:
            selected_collection = self.instance.collection

        if selected_collection:
            self._limit_related_querysets(selected_collection)
        else:
            self._limit_related_querysets(None)

    def _limit_related_querysets(self, collection):
        if collection is None:
            self.fields["category"].queryset = Category.objects.none()
            self.fields["manufacturer"].queryset = Manufacturer.objects.none()
            self.fields["status"].queryset = Status.objects.none()
            self.fields["parent_item"].queryset = Item.objects.none()
            self.fields["tags"].queryset = Tag.objects.none()
            return

        self.fields["category"].queryset = Category.objects.filter(
            collection=collection
        )
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(
            collection=collection
        )
        self.fields["status"].queryset = Status.objects.filter(collection=collection)
        parent_queryset = Item.objects.filter(collection=collection)
        if self.instance and self.instance.pk:
            parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
        self.fields["parent_item"].queryset = parent_queryset
        self.fields["tags"].queryset = Tag.objects.filter(collection=collection)

    def clean(self):
        cleaned_data = super().clean()
        collection = cleaned_data.get("collection")
        related_fields = [
            "category",
            "manufacturer",
            "status",
            "parent_item",
        ]
        for field_name in related_fields:
            value = cleaned_data.get(field_name)
            if value and collection and value.collection_id != collection.id:
                self.add_error(
                    field_name,
                    "Selection must belong to the chosen collection.",
                )

        tags = cleaned_data.get("tags")
        if tags and collection:
            for tag in tags:
                if tag.collection_id != collection.id:
                    self.add_error(
                        "tags",
                        "All tags must belong to the chosen collection.",
                    )
                    break

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer
        fields = ["name"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ["name"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["image", "is_thumbnail"]


class DocumentForm(forms.ModelForm):
    new_document_type = forms.CharField(required=False)

    class Meta:
        model = Document
        fields = ["document_type", "file"]

    def clean_new_document_type(self):
        return self.cleaned_data["new_document_type"].strip()


class LinkForm(forms.ModelForm):
    new_link_type = forms.CharField(required=False)

    class Meta:
        model = Link
        fields = ["link_type", "url"]

    def clean_new_link_type(self):
        return self.cleaned_data["new_link_type"].strip()


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
