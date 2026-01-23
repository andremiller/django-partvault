from django.db import models
from django.conf import settings

# TODO Add unique constraints
# TODO Add collection memberships (via CollectionMembership table, viewer, editor, admin)


class Collection(models.Model):
    """A collection of items"""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    asset_tag_prefix = models.CharField(max_length=2)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Category(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=60)

    def __str__(self) -> str:
        return self.name


class Manufacturer(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)

    def __str__(self) -> str:
        return self.name


class Status(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)

    class Meta:
        verbose_name_plural = "statuses"

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    # TODO Add index
    # TODO Add validation to ensure related fields belong to same collection (clean)

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    manufacturer = models.ForeignKey(
        Manufacturer, null=True, blank=True, on_delete=models.SET_NULL
    )
    model = models.CharField(max_length=120, blank=True)
    revision = models.CharField(max_length=120, blank=True)
    serial = models.CharField(
        max_length=120, blank=True
    )  # TODO Replace with m2m identifier table to cater for different identifier types
    status = models.ForeignKey(Status, null=True, blank=True, on_delete=models.SET_NULL)
    parent_item = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contained_items",
    )
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="items")
    acquired_on = models.DateField(blank=True, null=True)
    last_tested_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
