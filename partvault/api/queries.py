"""Scoped read queries; no reads change the active collection."""

from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from partvault.access import visible_collections, visible_items
from partvault.models import Category, LinkType, Manufacturer, Photo, Status, Tag

from .pagination import positive_integer, validate_query

LOOKUPS = {
    "categories": (Category, "category_id"),
    "manufacturers": (Manufacturer, "manufacturer_id"),
    "statuses": (Status, "status_id"),
    "tags": (Tag, "tags__id"),
    "link-types": (LinkType, None),
}
ORDERING = {
    "name": "name",
    "updated_at": "updated_at",
    "asset_tag": "asset_tag",
    "category": "category__name",
    "manufacturer": "manufacturer__name",
}
ITEM_FILTERS = {"search", "collection", "category", "manufacturer", "tag"}
PAGE_PARAMS = {"page", "page_size"}


def item_reads(user):
    thumbnail = Photo.objects.filter(item_id=OuterRef("pk")).exclude(image="")
    return (
        visible_items(user)
        .select_related(
            "collection__owner__profile", "category", "manufacturer", "status"
        )
        .prefetch_related(Prefetch("tags", queryset=Tag.objects.order_by("name", "id")))
        .annotate(
            thumbnail_id=Subquery(
                thumbnail.order_by("-is_thumbnail", "-uploaded_at", "-id").values("id")[
                    :1
                ]
            )
        )
    )


def filter_items(queryset, params, user):
    if "collection" in params:
        collection_id = positive_integer(params["collection"], "collection")
        collection = get_object_or_404(visible_collections(user), pk=collection_id)
        queryset = queryset.filter(collection=collection)
    for key in ("category", "manufacturer"):
        if key in params:
            queryset = queryset.filter(
                **{f"{key}_id": positive_integer(params[key], key)}
            )
    for value in set(params.getlist("tag")):
        queryset = queryset.filter(tags__id=positive_integer(value, "tag"))
    search = params.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(category__name__icontains=search)
            | Q(manufacturer__name__icontains=search)
            | Q(model__icontains=search)
            | Q(serial__icontains=search)
            | Q(tags__name__icontains=search)
            | Q(notes__icontains=search)
        )
    return queryset.distinct()


def ordered_items(queryset, params, user):
    validate_query(params, ITEM_FILTERS | PAGE_PARAMS | {"ordering"}, repeated={"tag"})
    ordering = params.get("ordering", "-updated_at")
    field = ORDERING.get(ordering.removeprefix("-"))
    if field is None:
        raise ValidationError(
            {
                "ordering": [
                    "Use name, updated_at, asset_tag, category or manufacturer; prefix - for descending."
                ]
            }
        )
    prefix = "-" if ordering.startswith("-") else ""
    return filter_items(queryset, params, user).order_by(
        f"{prefix}{field}", f"{prefix}id"
    )


def lookup_catalog(model, user):
    scope = Q(user__isnull=True)
    if user.is_authenticated:
        scope |= Q(user=user)
    return model.objects.filter(scope)
