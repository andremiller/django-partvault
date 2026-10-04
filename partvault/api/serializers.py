from django.urls import reverse
from rest_framework import serializers

from partvault.models import Collection, Document, Item, Link, Photo


class LabelSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class LookupSerializer(LabelSerializer):
    is_shared = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    def get_is_shared(self, obj):
        return obj.user_id is None

    def get_can_edit(self, obj):
        user = self.context["request"].user
        return user.is_authenticated and obj.user_id == user.id


class StatusLabelSerializer(LabelSerializer):
    color = serializers.CharField(read_only=True)


class StatusLookupSerializer(LookupSerializer):
    color = serializers.CharField(read_only=True)


class CollectionListSerializer(serializers.ModelSerializer):
    owner_code = serializers.CharField(source="owner.profile.user_code", default=None)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = (
            "id",
            "name",
            "collection_code",
            "owner_code",
            "is_public",
            "can_edit",
        )
        read_only_fields = fields

    def get_can_edit(self, obj):
        user = self.context["request"].user
        return user.is_authenticated and obj.owner_id == user.id


class CollectionDetailSerializer(CollectionListSerializer):
    item_count = serializers.IntegerField(read_only=True)
    items_url = serializers.SerializerMethodField()

    class Meta(CollectionListSerializer.Meta):
        fields = CollectionListSerializer.Meta.fields + ("item_count", "items_url")
        read_only_fields = fields

    def get_items_url(self, obj):
        return f"{reverse('api-v1:item-list')}?collection={obj.pk}"


class ItemListSerializer(serializers.ModelSerializer):
    collection = CollectionListSerializer(read_only=True)
    category = LabelSerializer(read_only=True)
    manufacturer = LabelSerializer(read_only=True)
    status = StatusLabelSerializer(read_only=True)
    tags = LabelSerializer(many=True, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = (
            "id",
            "name",
            "asset_tag",
            "collection",
            "category",
            "manufacturer",
            "model",
            "status",
            "tags",
            "thumbnail_url",
            "updated_at",
            "can_edit",
        )
        read_only_fields = fields

    def get_thumbnail_url(self, obj):
        if obj.thumbnail_id is None:
            return None
        return reverse("photo_image_scaled", args=[obj.thumbnail_id, 320])

    def get_can_edit(self, obj):
        user = self.context["request"].user
        return user.is_authenticated and obj.collection.owner_id == user.id


class ItemDetailSerializer(ItemListSerializer):
    # The view supplies a scoped parent, never the unfiltered parent_item relation.
    parent = ItemListSerializer(
        source="visible_parent", read_only=True, allow_null=True
    )

    class Meta(ItemListSerializer.Meta):
        fields = ItemListSerializer.Meta.fields + (
            "location",
            "revision",
            "serial",
            "notes",
            "manufacture_date",
            "release_date",
            "acquired_on",
            "last_tested_on",
            "created_at",
            "parent",
        )
        read_only_fields = fields


class PhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = ("id", "is_thumbnail", "uploaded_at", "url", "thumbnail_url")
        read_only_fields = fields

    def get_url(self, obj):
        return reverse("photo_image", args=[obj.pk]) if obj.image else None

    def get_thumbnail_url(self, obj):
        return reverse("photo_image_scaled", args=[obj.pk, 320]) if obj.image else None


class DocumentSerializer(serializers.ModelSerializer):
    document_type = LabelSerializer(read_only=True)
    filename = serializers.CharField(read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ("id", "document_type", "filename", "uploaded_at", "url")
        read_only_fields = fields

    def get_url(self, obj):
        return reverse("document_download", args=[obj.pk]) if obj.file else None


class LinkSerializer(serializers.ModelSerializer):
    link_type = LabelSerializer(read_only=True)

    class Meta:
        model = Link
        fields = ("id", "link_type", "url", "created_at")
        read_only_fields = fields
