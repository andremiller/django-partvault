"""Shared owner-scoped metadata validation and atomic item persistence."""

from copy import copy

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from .models import Category, Collection, Item, Manufacturer, Status, Tag

ITEM_WRITE_FIELDS = (
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
)
TAXONOMIES = {"category": Category, "manufacturer": Manufacturer, "status": Status}


def lock_item_owner(user):
    """Serialize cooperating item writes/moves/imports in deterministic order."""
    if not user.is_authenticated:
        raise PermissionDenied
    return list(
        Collection.objects.select_for_update().filter(owner=user).order_by("pk")
    )


def _choice(model, value, scope, field):
    if value is None:
        return None
    obj = model.objects.filter(scope, pk=value.pk).first()
    if obj is None:
        raise ValidationError({field: "Select an available choice."})
    return obj


def _descendants(item, owner_id):
    seen = {item.pk}
    frontier = [item.pk]
    descendants = []
    while frontier:
        children = list(
            Item.objects.filter(parent_item_id__in=frontier)
            .select_related("collection", "category", "manufacturer", "status")
            .prefetch_related("tags")
            .order_by("pk")
        )
        frontier = []
        for child in children:
            if child.pk in seen:
                raise ValidationError(
                    {"parent_item": "Existing containment contains a cycle."}
                )
            if (
                child.collection.owner_id != owner_id
                or child.collection_id != item.collection_id
            ):
                raise ValidationError(
                    {
                        "collection": "Contents have inconsistent ownership or placement. Repair them before moving this item."
                    }
                )
            for field in TAXONOMIES:
                value = getattr(child, field)
                if value and value.user_id not in (None, owner_id):
                    raise ValidationError(
                        {
                            "collection": "Contents have unavailable lookup values. Repair them before moving this item."
                        }
                    )
            if any(tag.user_id not in (None, owner_id) for tag in child.tags.all()):
                raise ValidationError(
                    {
                        "collection": "Contents have unavailable tags. Repair them before moving this item."
                    }
                )
            seen.add(child.pk)
            frontier.append(child.pk)
            descendants.append(child.pk)
    return descendants


def validate_item_write(user, instance, data):
    """Validate the resulting state; return a fresh candidate and moved child IDs.

    Call again inside the write transaction, even after form/serializer validation.
    Scalar conversion/length/date validation belongs to the form/serializer.
    """
    if not user or not user.is_authenticated:
        raise ValidationError({"collection": "Select a collection you own."})
    unknown = set(data) - set(ITEM_WRITE_FIELDS)
    if unknown:
        raise ValidationError(
            {field: "This field cannot be written." for field in unknown}
        )
    original = (
        Item.objects.select_related("collection").filter(pk=instance.pk).first()
        if instance and instance.pk
        else None
    )
    if instance and instance.pk and original is None:
        raise Item.DoesNotExist
    if original and original.collection.owner_id != user.pk:
        raise PermissionDenied
    candidate = copy(original) if original else Item()
    for field, value in data.items():
        if field != "tags":
            setattr(candidate, field, value)
    collection = _choice(
        Collection,
        candidate.collection if candidate.collection_id else None,
        Q(owner=user),
        "collection",
    )
    if collection is None:
        raise ValidationError({"collection": "Select a collection you own."})
    candidate.collection = collection
    scope = Q(user=user) | Q(user__isnull=True)
    for field, model in TAXONOMIES.items():
        setattr(
            candidate, field, _choice(model, getattr(candidate, field), scope, field)
        )
    tags = (
        list(data["tags"])
        if "tags" in data
        else list(original.tags.all())
        if original
        else []
    )
    candidate.write_tags = [_choice(Tag, tag, scope, "tags") for tag in tags]
    parent = _choice(
        Item,
        candidate.parent_item if candidate.parent_item_id else None,
        Q(collection=collection),
        "parent_item",
    )
    candidate.parent_item = parent
    seen = {candidate.pk} if candidate.pk else set()
    while parent:
        if parent.pk in seen:
            raise ValidationError(
                {
                    "parent_item": "An item cannot be contained in itself or its descendants, or in a cyclic hierarchy."
                }
            )
        seen.add(parent.pk)
        if parent.collection_id != collection.pk:
            raise ValidationError(
                {
                    "parent_item": "The parent hierarchy must belong to the chosen collection."
                }
            )
        parent = (
            Item.objects.filter(pk=parent.parent_item_id).first()
            if parent.parent_item_id
            else None
        )
    descendants = (
        _descendants(original, user.pk)
        if original and original.collection_id != collection.pk
        else []
    )
    return candidate, descendants


@transaction.atomic
def save_item(user, instance, data):
    lock_item_owner(user)
    candidate, descendants = validate_item_write(user, instance, data)
    try:
        candidate.save()  # Retains auto-name and generated/reserved asset-tag semantics.
    except ValueError as exc:
        raise ValidationError({"__all__": str(exc)}) from exc
    candidate.tags.set(candidate.write_tags)
    if descendants:
        Item.objects.filter(pk__in=descendants).update(collection=candidate.collection)
    return candidate


@transaction.atomic
def delete_item(user, instance):
    lock_item_owner(user)
    item = Item.objects.get(pk=instance.pk, collection__owner=user)
    # Model signals retain attachment cleanup and assigned-tag voiding; children
    # are detached by SET_NULL, not recursively deleted.
    item.delete()
