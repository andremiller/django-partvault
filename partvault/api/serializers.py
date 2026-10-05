from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework import serializers

from partvault.item_services import (
    ITEM_WRITE_FIELDS,
    TAXONOMIES,
    save_item,
    validate_item_write,
)
from partvault.models import (
    Category,
    Collection,
    Document,
    Item,
    Link,
    Manufacturer,
    Photo,
    Status,
    Tag,
)


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


class StrictWriteSerializer(serializers.Serializer):
    """Reject server-controlled and unknown fields instead of silently ignoring."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {field: ["This field cannot be written."] for field in unknown}
                )
        return super().to_internal_value(data)


def write_error(exc):
    detail = (
        exc.message_dict
        if hasattr(exc, "message_dict")
        else {"non_field_errors": exc.messages}
    )
    return serializers.ValidationError(
        {
            ("non_field_errors" if key == "__all__" else key): value
            for key, value in detail.items()
        }
    )


class WriteRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        kwargs["pk_field"] = serializers.IntegerField(
            min_value=1, max_value=9223372036854775807
        )
        super().__init__(**kwargs)


class ItemWriteSerializer(StrictWriteSerializer, serializers.ModelSerializer):
    collection = WriteRelatedField(queryset=Collection.objects.none())
    category = WriteRelatedField(
        queryset=Category.objects.none(), required=False, allow_null=True
    )
    manufacturer = WriteRelatedField(
        queryset=Manufacturer.objects.none(), required=False, allow_null=True
    )
    status = WriteRelatedField(
        queryset=Status.objects.none(), required=False, allow_null=True
    )
    parent_item = WriteRelatedField(
        queryset=Item.objects.none(), required=False, allow_null=True
    )
    tags = WriteRelatedField(queryset=Tag.objects.none(), many=True, required=False)

    class Meta:
        model = Item
        fields = ITEM_WRITE_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        if not user.is_authenticated:
            return
        self.fields["collection"].queryset = Collection.objects.filter(owner=user)
        self.fields["parent_item"].queryset = Item.objects.filter(
            collection__owner=user
        )
        for field, model in TAXONOMIES.items():
            self.fields[field].queryset = model.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            )
        self.fields["tags"].child_relation.queryset = Tag.objects.filter(
            Q(user=user) | Q(user__isnull=True)
        )
        for field in ("collection", "parent_item", *TAXONOMIES):
            self.fields[field].error_messages["does_not_exist"] = (
                "Select an available choice."
            )
        self.fields["tags"].child_relation.error_messages["does_not_exist"] = (
            "Select an available choice."
        )

    def validate(self, attrs):
        try:
            validate_item_write(self.context["request"].user, self.instance, attrs)
        except DjangoValidationError as exc:
            raise write_error(exc) from exc
        except Item.DoesNotExist as exc:
            raise NotFound() from exc
        return attrs

    def create(self, validated_data):
        return self._save(None, validated_data)

    def update(self, instance, validated_data):
        return self._save(instance, validated_data)

    def _save(self, instance, data):
        try:
            return save_item(self.context["request"].user, instance, data)
        except DjangoValidationError as exc:
            raise write_error(exc) from exc
        except Item.DoesNotExist as exc:
            raise NotFound() from exc


class LookupWriteSerializer(StrictWriteSerializer):
    def __init__(self, *args, model, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.fields["name"] = serializers.CharField(
            max_length=model._meta.get_field("name").max_length
        )
        if model is Status:
            self.fields["color"] = serializers.ChoiceField(
                choices=Status.Color.choices, required=False, default=Status.Color.INFO
            )

    def create(self, validated_data):
        return self.model.objects.create(
            user=self.context["request"].user, **validated_data
        )

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
