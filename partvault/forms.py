import re

from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q

from .item_services import ITEM_WRITE_FIELDS, save_item, validate_item_write

from .models import (
    AssetTagSequence,
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


class AssetTagSheetForm(forms.Form):
    tags = forms.CharField(
        label="Tags and ranges",
        max_length=40000,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "000-111,113,115,116-200"}
        ),
        help_text=(
            "Enter base-36 tags (0-9 and A-Z), separated by commas. "
            "For example: 1-A,C,F,10-1Z combines ranges and individual tags. "
            "Ranges include both endpoints. Order and repeated tags are preserved. "
            "Maximum 2,400 stickers per download."
        ),
    )
    prefix = forms.CharField(
        label="Label prefix letter",
        max_length=1,
        help_text="One letter, printed before the six-character tag; excluded from the QR URL.",
    )

    def clean_prefix(self):
        prefix = self.cleaned_data["prefix"]
        if not re.fullmatch(r"[A-Za-z]", prefix):
            raise ValidationError("Enter one letter from A to Z.")
        return prefix.upper()

    def clean_tags(self):
        ranges = []
        count = 0
        for entry in self.cleaned_data["tags"].split(","):
            match = re.fullmatch(
                r"([A-Za-z0-9]{1,6})(?:\s*-\s*([A-Za-z0-9]{1,6}))?",
                entry.strip(),
            )
            if not match:
                raise ValidationError(
                    "Enter comma-separated tags or ranges, using 1-6 letters or digits "
                    "per tag, for example: 000-111,113,115,116-200."
                )
            start = int(match[1], 36)
            end = int(match[2], 36) if match[2] else start
            if end < start:
                raise ValidationError("Range endpoints must be in ascending order.")
            count += end - start + 1
            if count > 2400:
                raise ValidationError(
                    "Select at most 2,400 stickers per download, including repeats."
                )
            ranges.append((start, end))
        return [
            AssetTagSequence._to_base36(value).zfill(6)
            for start, end in ranges
            for value in range(start, end + 1)
        ]


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
            "location",
            "manufacturer",
            "model",
            "revision",
            "serial",
            "manufacture_date",
            "release_date",
            "status",
            "parent_item",
            "tags",
            "notes",
            "acquired_on",
            "last_tested_on",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
            "manufacture_date": forms.DateInput(attrs={"type": "date"}),
            "release_date": forms.DateInput(attrs={"type": "date"}),
            "acquired_on": forms.DateInput(attrs={"type": "date"}),
            "last_tested_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, collection=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields["collection"].queryset = Collection.objects.filter(owner=user)
        else:
            self.fields["collection"].queryset = Collection.objects.none()

        selected_collection = collection
        if self.is_bound:
            collection_id = self.data.get("collection")
            if collection_id and str(collection_id).isdecimal():
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

        owner = collection.owner
        owner_id = owner.id
        user_filter = Q(user=owner) | Q(user__isnull=True)
        self.fields["category"].queryset = Category.objects.filter(user_filter)
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(user_filter)
        self.fields["status"].queryset = Status.objects.filter(user_filter)
        parent_queryset = Item.objects.filter(collection=collection)
        if self.instance and self.instance.pk:
            parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
        self.fields["parent_item"].queryset = parent_queryset
        self.fields["tags"].queryset = Tag.objects.filter(user_filter)

        def label_with_custom_marker(obj):
            if obj.user_id == owner_id:
                return f"🖋️ {obj}"
            if obj.user_id is None:
                return f"🌐 {obj}"
            return str(obj)

        self.fields["category"].label_from_instance = label_with_custom_marker
        self.fields["manufacturer"].label_from_instance = label_with_custom_marker
        self.fields["status"].label_from_instance = label_with_custom_marker
        self.fields["tags"].label_from_instance = label_with_custom_marker

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()

    def clean_location(self):
        return (self.cleaned_data.get("location") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            try:
                validate_item_write(self.user, self.instance, cleaned_data)
            except ValidationError as exc:
                self.add_error(None, exc)
            except Item.DoesNotExist:
                self.add_error(None, "This item is no longer available.")
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        if self.errors:
            raise ValueError(
                "The item could not be saved because the data did not validate."
            )
        self.instance = save_item(
            self.user,
            self.instance,
            {field: self.cleaned_data[field] for field in ITEM_WRITE_FIELDS},
        )
        return self.instance


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
        fields = ["name", "color"]

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
        labels = {
            "is_thumbnail": "Thumb",
        }
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={"accept": "image/*", "capture": "environment"}
            ),
        }


class DocumentForm(forms.ModelForm):
    new_document_type = forms.CharField(required=False)

    class Meta:
        model = Document
        fields = ["document_type", "file"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_filter = Q(user=user) | Q(user__isnull=True)
            self.fields["document_type"].queryset = self.fields[
                "document_type"
            ].queryset.filter(user_filter)
            user_id = user.id

            def label_with_custom_marker(obj):
                if obj.user_id == user_id:
                    return f"🖋️ {obj}"
                if obj.user_id is None:
                    return f"🌐 {obj}"
                return str(obj)

            self.fields["document_type"].label_from_instance = label_with_custom_marker
        else:
            self.fields["document_type"].queryset = self.fields[
                "document_type"
            ].queryset.none()

    def clean_new_document_type(self):
        return self.cleaned_data["new_document_type"].strip()


class LinkForm(forms.ModelForm):
    new_link_type = forms.CharField(required=False)

    class Meta:
        model = Link
        fields = ["link_type", "url"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            user_filter = Q(user=user) | Q(user__isnull=True)
            self.fields["link_type"].queryset = self.fields[
                "link_type"
            ].queryset.filter(user_filter)
            user_id = user.id

            def label_with_custom_marker(obj):
                if obj.user_id == user_id:
                    return f"🖋️ {obj}"
                if obj.user_id is None:
                    return f"🌐 {obj}"
                return str(obj)

            self.fields["link_type"].label_from_instance = label_with_custom_marker
        else:
            self.fields["link_type"].queryset = self.fields["link_type"].queryset.none()

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
