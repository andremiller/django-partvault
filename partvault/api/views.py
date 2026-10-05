from django.db import transaction
from django.db.models import Count
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from partvault.access import visible_collections, visible_items
from partvault.item_services import delete_item
from partvault.models import Collection, Document, Item, Link, Photo, Profile

from .pagination import validate_query
from .queries import (
    ITEM_FILTERS,
    LOOKUPS,
    PAGE_PARAMS,
    filter_items,
    item_reads,
    lookup_catalog,
    ordered_items,
)
from .serializers import (
    CollectionDetailSerializer,
    CollectionListSerializer,
    DocumentSerializer,
    ItemDetailSerializer,
    ItemListSerializer,
    ItemWriteSerializer,
    LookupWriteSerializer,
    LabelSerializer,
    LinkSerializer,
    LookupSerializer,
    PhotoSerializer,
    StatusLabelSerializer,
    StatusLookupSerializer,
)


class PrivateResponseMixin:
    """Even public reads can contain session-dependent capabilities/visible rows."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


class ReadMixin(PrivateResponseMixin):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")


class ReadWriteMixin(PrivateResponseMixin):
    def get_permissions(self):
        permission = (
            AllowAny
            if self.request.method in ("GET", "HEAD", "OPTIONS")
            else IsAuthenticated
        )
        return [permission()]


class SessionView(ReadMixin, APIView):
    def get(self, request):
        validate_query(request.query_params, set())
        user_data = profile_data = active_collection = None
        if request.user.is_authenticated:
            user = request.user
            user_data = {
                "id": user.pk,
                "username": user.get_username(),
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            profile = Profile.objects.filter(user=user).first()
            if profile is not None:
                profile_data = {"user_code": profile.user_code}
                # Ignore a stale/foreign active pointer without changing it on GET.
                active = (
                    Collection.objects.filter(
                        pk=profile.active_collection_id, owner=user
                    )
                    .select_related("owner__profile")
                    .first()
                )
                if active is not None:
                    active_collection = CollectionListSerializer(
                        active, context={"request": request}
                    ).data
        return Response(
            {
                "user": user_data,
                "profile": profile_data,
                "active_collection": active_collection,
                "csrf_token": get_token(request),
            }
        )


class CollectionActivateView(PrivateResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("post", "options")

    def post(self, request, pk):
        validate_query(request.query_params, set())
        collection = get_object_or_404(
            Collection.objects.select_related("owner__profile"),
            pk=pk,
            owner=request.user,
        )
        # Profile requires a unique user code. Do not invent one on bootstrap/activate.
        updated = Profile.objects.filter(user=request.user).update(
            active_collection=collection
        )
        if not updated:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "Your profile is missing. Ask an administrator to create a profile with a unique user code before activating a collection."
                    ]
                }
            )
        return Response(
            {
                "active_collection": CollectionListSerializer(
                    collection, context={"request": request}
                ).data
            }
        )


class CollectionListView(ReadMixin, ListAPIView):
    serializer_class = CollectionListSerializer

    def get_queryset(self):
        params = self.request.query_params
        validate_query(params, PAGE_PARAMS | {"search"})
        queryset = visible_collections(self.request.user).select_related(
            "owner__profile"
        )
        if search := params.get("search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name", "id")


class CollectionDetailView(ReadMixin, RetrieveAPIView):
    serializer_class = CollectionDetailSerializer

    def get_queryset(self):
        validate_query(self.request.query_params, set())
        return (
            visible_collections(self.request.user)
            .select_related("owner__profile")
            .annotate(item_count=Count("item"))
        )


class ItemListView(ReadWriteMixin, ListAPIView):
    serializer_class = ItemListSerializer
    http_method_names = ("get", "head", "post", "options")

    def get_serializer_class(self):
        return (
            ItemWriteSerializer if self.request.method == "POST" else ItemListSerializer
        )

    def get_queryset(self):
        return ordered_items(
            item_reads(self.request.user), self.request.query_params, self.request.user
        )

    def post(self, request):
        validate_query(request.query_params, set())
        serializer = ItemWriteSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        item = item_reads(request.user).get(pk=item.pk)
        return Response(
            item_detail_data(self, item),
            status=201,
            headers={
                "Location": reverse("api-v1:item-detail", args=[item.pk]),
            },
        )


def nested_resource(user, item_id, resource):
    if resource == "children":
        return item_reads(user).filter(parent_item_id=item_id).order_by(
            "name", "id"
        ), ItemListSerializer
    if resource == "photos":
        return Photo.objects.filter(item_id=item_id).order_by(
            "-is_thumbnail", "-uploaded_at", "-id"
        ), PhotoSerializer
    if resource == "documents":
        return Document.objects.filter(item_id=item_id).select_related(
            "document_type"
        ).order_by("-uploaded_at", "-id"), DocumentSerializer
    if resource == "links":
        return Link.objects.filter(item_id=item_id).select_related(
            "link_type"
        ).order_by("-created_at", "-id"), LinkSerializer
    raise NotFound()


class ItemDetailView(ReadWriteMixin, RetrieveAPIView):
    serializer_class = ItemDetailSerializer
    http_method_names = ("get", "head", "patch", "delete", "options")

    def get_queryset(self):
        validate_query(self.request.query_params, set())
        queryset = item_reads(self.request.user)
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            queryset = queryset.filter(collection__owner=self.request.user)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        return Response(item_detail_data(self, item))

    def patch(self, request, *args, **kwargs):
        serializer = ItemWriteSerializer(
            self.get_object(),
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        item = item_reads(request.user).get(pk=item.pk)
        return Response(item_detail_data(self, item))

    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        try:
            delete_item(request.user, item)
        except Item.DoesNotExist as exc:
            raise NotFound() from exc
        return Response(status=204)


def item_detail_data(view, item):
    request = view.request
    item.visible_parent = (
        item_reads(request.user).filter(pk=item.parent_item_id).first()
        if item.parent_item_id
        else None
    )
    data = ItemDetailSerializer(item, context=view.get_serializer_context()).data
    for resource in ("children", "photos", "documents", "links"):
        queryset, serializer = nested_resource(request.user, item.pk, resource)
        count = queryset.count()
        url = reverse(f"api-v1:item-{resource}", args=[item.pk])
        data[resource] = {
            "count": count,
            "next": f"{url}?page=2&page_size=10" if count > 10 else None,
            "previous": None,
            "results": serializer(
                queryset[:10], many=True, context=view.get_serializer_context()
            ).data,
        }
    return data


class ItemResourceView(ReadMixin, GenericAPIView):
    resource = None

    def get(self, request, item_id, resource_id=None):
        validate_query(
            request.query_params, PAGE_PARAMS if resource_id is None else set()
        )
        get_object_or_404(visible_items(request.user), pk=item_id)
        queryset, serializer = nested_resource(request.user, item_id, self.resource)
        context = self.get_serializer_context()
        if resource_id is not None:
            return Response(
                serializer(
                    get_object_or_404(queryset, pk=resource_id), context=context
                ).data
            )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            serializer(page, many=True, context=context).data
        )


class LookupListView(ReadWriteMixin, ListAPIView):
    lookup = None
    http_method_names = ("get", "head", "post", "options")

    def get_serializer_class(self):
        return StatusLookupSerializer if self.lookup == "statuses" else LookupSerializer

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "POST" and not args:
            model, _ = LOOKUPS[self.lookup]
            kwargs.setdefault("context", self.get_serializer_context())
            return LookupWriteSerializer(model=model, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        params = self.request.query_params
        validate_query(params, PAGE_PARAMS | {"search"})
        model, _ = LOOKUPS[self.lookup]
        queryset = lookup_catalog(model, self.request.user)
        if search := params.get("search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name", "id")

    @transaction.atomic
    def post(self, request):
        validate_query(request.query_params, set())
        model, _ = LOOKUPS[self.lookup]
        serializer = LookupWriteSerializer(
            data=request.data, model=model, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            self.get_serializer(obj).data,
            status=201,
            headers={
                "Location": reverse(f"api-v1:{self.lookup}-detail", args=[obj.pk]),
            },
        )


class LookupDetailView(ReadWriteMixin, GenericAPIView):
    lookup = None
    http_method_names = ("get", "head", "patch", "delete", "options")

    def get_serializer_class(self):
        return StatusLookupSerializer if self.lookup == "statuses" else LookupSerializer

    def get(self, request, pk):
        validate_query(request.query_params, set())
        model, _ = LOOKUPS[self.lookup]
        obj = get_object_or_404(lookup_catalog(model, request.user), pk=pk)
        return Response(self.get_serializer(obj).data)

    def owned_object(self, pk):
        validate_query(self.request.query_params, set())
        model, _ = LOOKUPS[self.lookup]
        return get_object_or_404(
            model.objects.select_for_update(), pk=pk, user=self.request.user
        )

    @transaction.atomic
    def patch(self, request, pk):
        obj = self.owned_object(pk)
        serializer = LookupWriteSerializer(
            obj,
            data=request.data,
            partial=True,
            model=type(obj),
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(self.get_serializer(obj).data)

    @transaction.atomic
    def delete(self, request, pk):
        obj = self.owned_object(pk)
        obj.delete()  # Existing SET_NULL/M2M cleanup semantics are retained.
        return Response(status=204)


class FilterFacetView(ReadMixin, ListAPIView):
    def get_serializer_class(self):
        return (
            StatusLabelSerializer
            if self.request.query_params.get("facet") == "statuses"
            else LabelSerializer
        )

    def get_queryset(self):
        params = self.request.query_params
        validate_query(
            params,
            ITEM_FILTERS | PAGE_PARAMS | {"facet", "facet_search"},
            repeated={"tag"},
        )
        facet = params.get("facet")
        if facet not in {
            "collections",
            "categories",
            "manufacturers",
            "statuses",
            "tags",
        }:
            raise ValidationError(
                {
                    "facet": [
                        "Choose collections, categories, manufacturers, statuses or tags."
                    ]
                }
            )
        # Match all supplied filters, including the selected facet's filter.
        items = filter_items(
            visible_items(self.request.user), params, self.request.user
        )
        # Resolve membership first, then collect all labels on matching records.
        # Reusing a tag-filter join would otherwise hide their other tags.
        matching_items = (
            visible_items(self.request.user)
            .filter(pk__in=items.order_by().values("pk"))
            .order_by()
        )
        if facet == "collections":
            queryset = visible_collections(self.request.user).filter(
                pk__in=matching_items.values("collection_id")
            )
        else:
            model, field = LOOKUPS[facet]
            queryset = model.objects.filter(pk__in=matching_items.values(field))
        if search := params.get("facet_search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name", "id")


class MissingEndpointView(ReadMixin, APIView):
    def get(self, request, **kwargs):
        raise NotFound()
