"""Shared public-or-owner read scopes (including legacy inconsistent relations)."""

from django.db.models import Q

from .models import Collection, Item


def visible_collections(user):
    scope = Q(is_public=True)
    if user.is_authenticated:
        scope |= Q(owner=user)
    return Collection.objects.filter(scope)


def visible_items(user):
    return Item.objects.filter(collection__in=visible_collections(user))
