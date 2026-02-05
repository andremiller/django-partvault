import os
from datetime import datetime

from django.db import models, transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator

# TODO Add unique constraints
# TODO Add collection memberships (via CollectionMembership table, viewer, editor, admin)


class Collection(models.Model):
    """A collection of items"""

    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    collection_code = models.CharField(
        max_length=3,
        validators=[MinLengthValidator(1)],
        help_text=(
            "Required. 1 to 3 alphanumeric characters, code for this collection, for display only."
        ),
    )
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def owner_code(self) -> str:
        return self.owner.profile.user_code


class Profile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    user_code = models.CharField(
        max_length=3,
        unique=True,
        validators=[MinLengthValidator(1)],
        help_text=(
            "Required. 1 to 3 alphanumeric characters, unique to you, displayed to others."
        ),
    )
    active_collection = models.ForeignKey(
        "Collection",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_for_profiles",
    )

    def __str__(self) -> str:
        return f"Profile for {self.user}"


class Category(models.Model):
    user = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    user = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=60)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Manufacturer(models.Model):
    user = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Status(models.Model):
    class Color(models.TextChoices):
        PRIMARY = "bg-primary", "Primary"
        SECONDARY = "bg-secondary", "Secondary"
        SUCCESS = "bg-success", "Success"
        DANGER = "bg-danger", "Danger"
        WARNING = "bg-warning", "Warning"
        INFO = "bg-info", "Info"
        LIGHT = "bg-light", "Light"
        DARK = "bg-dark", "Dark"

    user = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)
    color = models.CharField(
        max_length=20,
        choices=Color.choices,
        default=Color.INFO,
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "statuses"

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    # TODO Add index
    # TODO Add validation to ensure related fields belong to same collection (clean)

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    location = models.CharField(max_length=120, blank=True)
    manufacturer = models.ForeignKey(
        Manufacturer, null=True, blank=True, on_delete=models.SET_NULL
    )
    model = models.CharField(max_length=120, blank=True)
    revision = models.CharField(max_length=120, blank=True)
    serial = models.CharField(
        max_length=120, blank=True
    )  # TODO Replace with m2m identifier table to cater for different identifier types
    status = models.ForeignKey(Status, null=True, blank=True, on_delete=models.SET_NULL)
    asset_tag = models.CharField(max_length=6, unique=True, null=True, blank=True)
    parent_item = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contained_items",
    )
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="items")
    release_date = models.DateField(blank=True, null=True)
    acquired_on = models.DateField(blank=True, null=True)
    last_tested_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not (self.name or "").strip():
            name_parts = []
            if self.manufacturer:
                name_parts.append(self.manufacturer.name)
            model_name = (self.model or "").strip()
            if model_name:
                name_parts.append(model_name)
            self.name = " ".join(name_parts)
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.asset_tag:
            sequence = AssetTagSequence.assign(self.collection.owner, self)
            self.asset_tag = sequence.asset_tag
            super().save(update_fields=["asset_tag"])


def upload_path_base(item):
    """Upload path base, relative to MEDIA_ROOT"""
    return f"uploads/{item.collection.id}/{item.asset_tag}"


def upload_path_document(instance, filename):
    """Document upload path"""
    filename = "".join(
        char for char in filename.lower() if char.isalnum() or char in "-."
    )
    path_base = upload_path_base(instance.item)
    return f"{path_base}/{filename}"


def upload_path_photo(instance, filename):
    """Photo upload"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    extension = os.path.splitext(filename)[1].lower()
    filename = f"{timestamp}{extension}"
    path_base = upload_path_base(instance.item)
    return f"{path_base}/{filename}"


class DocumentType(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    file = models.FileField(upload_to=upload_path_document, max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type or 'Document'}: {self.file.name}"


class LinkType(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)

    def __str__(self) -> str:
        return self.name


class Link(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    link_type = models.ForeignKey(
        LinkType, on_delete=models.SET_NULL, null=True, blank=True
    )
    url = models.URLField(max_length=2048)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.link_type or 'Link'}: {self.url}"


class Photo(models.Model):
    # TODO Ensure there is only one thumbnail image set
    # TODO Auto generate lower resolution thumbnails (and delete old if thumbnail changes)
    # TODO Delete image on disk if deleted from DB
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=upload_path_photo)
    is_thumbnail = models.BooleanField(
        default=False, help_text="Photo used as thumbnail"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.item.name}"


@receiver(post_delete, sender=Document)
def delete_document_file_on_delete(sender, instance, **kwargs):
    if instance.file and instance.file.name:
        instance.file.delete(save=False)


@receiver(pre_save, sender=Document)
def delete_document_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = Document.objects.get(pk=instance.pk)
    except Document.DoesNotExist:
        return
    if previous.file and previous.file.name and previous.file != instance.file:
        previous.file.delete(save=False)


@receiver(post_delete, sender=Photo)
def delete_photo_file_on_delete(sender, instance, **kwargs):
    if instance.image and instance.image.name:
        instance.image.delete(save=False)


@receiver(pre_save, sender=Photo)
def delete_photo_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = Photo.objects.get(pk=instance.pk)
    except Photo.DoesNotExist:
        return
    if previous.image and previous.image.name and previous.image != instance.image:
        previous.image.delete(save=False)


class AssetTagSequence(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved"
        ASSIGNED = "assigned"
        VOID = "void"

    asset_tag = models.CharField(
        max_length=6, unique=True, editable=False, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RESERVED
    )
    reserved_by = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    assigned_item = models.OneToOneField(
        Item, null=True, blank=True, on_delete=models.SET_NULL
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.asset_tag or "")

    @staticmethod
    def _to_base36(value: int) -> str:
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if value <= 0:
            return "0"
        chars = []
        while value:
            value, rem = divmod(value, 36)
            chars.append(alphabet[rem])
        return "".join(reversed(chars))

    @classmethod
    def reserve(cls, user):
        reserved_count = cls.objects.filter(
            reserved_by=user, status=cls.Status.RESERVED
        ).count()
        if reserved_count >= 1000:
            raise ValueError("User already has 1000 reserved asset tags")
        return cls.objects.create(reserved_by=user)

    @classmethod
    def assign(cls, user, item):
        with transaction.atomic():
            asset_tag = (
                cls.objects.select_for_update(skip_locked=True)
                .filter(
                    reserved_by=user,
                    status=cls.Status.RESERVED,
                    assigned_item__isnull=True,
                )
                .order_by("reserved_at")
                .first()
            )
            if asset_tag is None:
                asset_tag = cls.reserve(user)
            asset_tag.status = cls.Status.ASSIGNED
            asset_tag.assigned_item = item
            asset_tag.assigned_at = datetime.now()
            asset_tag.save(update_fields=["status", "assigned_item", "assigned_at"])
            return asset_tag

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.asset_tag:
            self.asset_tag = self._to_base36(self.id).zfill(6)
            super().save(update_fields=["asset_tag"])


@receiver(post_delete, sender=Item)
def void_asset_tag_on_item_delete(sender, instance, **kwargs):
    if not instance.asset_tag:
        return
    AssetTagSequence.objects.filter(asset_tag=instance.asset_tag).update(
        status=AssetTagSequence.Status.VOID
    )
