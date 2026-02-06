from io import BytesIO
from mimetypes import guess_type

from PIL import Image, ImageOps
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Max, Prefetch, Q
from django.forms import formset_factory, inlineformset_factory, modelformset_factory
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import (
    AssetTagSequence,
    Category,
    Collection,
    Document,
    Item,
    Link,
    LinkType,
    Manufacturer,
    Photo,
    Profile,
    Status,
    Tag,
)
from .forms import (
    CategoryForm,
    CollectionForm,
    DocumentForm,
    ItemForm,
    LinkForm,
    ManufacturerForm,
    PhotoForm,
    ProfileForm,
    SignupForm,
    StatusForm,
    TagForm,
    UserProfileForm,
)


def _attach_collection_preview_photos(collections):
    collection_list = list(collections)
    if not collection_list:
        return collection_list

    for collection in collection_list:
        preview_photos = []
        for item in collection.items_with_ordered_photos:
            if not item.ordered_photos:
                continue
            preview_photos.append(item.ordered_photos[0])
            if len(preview_photos) >= 4:
                break
        collection.thumbnail_photos = preview_photos

    return collection_list


def _base36_to_int(value: str) -> int:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    for char in value.upper():
        total = total * 36 + alphabet.index(char)
    return total


def _int_to_base36(value: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if value <= 0:
        return "0"
    chars = []
    while value:
        value, rem = divmod(value, 36)
        chars.append(alphabet[rem])
    return "".join(reversed(chars))


def _user_can_view_photo(request, photo: Photo) -> bool:
    if photo.item.collection.is_public:
        return True
    if not request.user.is_authenticated:
        return False
    return photo.item.collection.owner_id == request.user.id


def _serialize_resized_image(image: Image.Image, output_format: str) -> bytes:
    buffer = BytesIO()
    if output_format == "JPEG":
        image = image.convert("RGB")
    image.save(buffer, format=output_format, optimize=True)
    return buffer.getvalue()


def photo_image(request, photo_id, long_edge=None):
    photo = get_object_or_404(
        Photo.objects.select_related("item__collection"), pk=photo_id
    )
    if not photo.image:
        raise Http404("Photo not found")
    if not _user_can_view_photo(request, photo):
        raise Http404("Photo not found")

    content_type, _ = guess_type(photo.image.name)
    if not content_type:
        content_type = "application/octet-stream"

    if long_edge is None:
        photo.image.open("rb")
        return FileResponse(photo.image, content_type=content_type)

    if long_edge < 1:
        return HttpResponse(b"Invalid image size.", status=400)

    photo.image.open("rb")
    image = Image.open(photo.image)
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    max_edge = max(width, height)
    if long_edge >= max_edge:
        photo.image.seek(0)
        return FileResponse(photo.image, content_type=content_type)

    scale = long_edge / max_edge
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    output_format = image.format or "JPEG"
    content_type = Image.MIME.get(output_format, "image/jpeg")
    data = _serialize_resized_image(resized, output_format)
    return HttpResponse(data, content_type=content_type)


def index(request):
    photo_prefetch = Prefetch(
        "photo_set",
        queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
        to_attr="ordered_photos",
    )
    item_prefetch = Prefetch(
        "item_set",
        queryset=Item.objects.prefetch_related(photo_prefetch).order_by("-updated_at"),
        to_attr="items_with_ordered_photos",
    )
    my_collections = Collection.objects.none()
    if request.user.is_authenticated:
        my_collections = (
            Collection.objects.filter(owner=request.user)
            .annotate(
                last_item_updated_at=Max("item__updated_at"),
                item_count=Count("item", distinct=True),
            )
            .prefetch_related(item_prefetch)
        )
        public_collections = (
            Collection.objects.filter(is_public=True)
            .exclude(owner=request.user)
            .annotate(
                last_item_updated_at=Max("item__updated_at"),
                item_count=Count("item", distinct=True),
            )
            .filter(item_count__gt=0)
            .prefetch_related(item_prefetch)
        )
    else:
        public_collections = Collection.objects.filter(is_public=True).annotate(
            last_item_updated_at=Max("item__updated_at"),
            item_count=Count("item", distinct=True),
        )
        public_collections = public_collections.filter(
            item_count__gt=0,
        ).prefetch_related(item_prefetch)
    my_collections = _attach_collection_preview_photos(my_collections)
    public_collections = _attach_collection_preview_photos(public_collections)
    context = {
        "my_collections": my_collections,
        "public_collections": public_collections,
    }
    return render(request, "partvault/index.html", context)


def items(request, collection_id):
    collection_queryset = Collection.objects.all()
    if not request.user.is_authenticated:
        collection_queryset = collection_queryset.filter(is_public=True)
    else:
        collection_queryset = collection_queryset.filter(
            Q(is_public=True) | Q(owner=request.user)
        )
    collection = get_object_or_404(collection_queryset, pk=collection_id)
    if request.user.is_authenticated and collection.owner_id == request.user.id:
        if request.user.profile.active_collection_id != collection.id:
            request.user.profile.active_collection = collection
            request.user.profile.save(update_fields=["active_collection"])
    item_list = (
        Item.objects.filter(collection=collection)
        .select_related("category", "manufacturer", "status")
        .prefetch_related("tags")
        .prefetch_related(
            Prefetch(
                "photo_set",
                queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
                to_attr="ordered_photos",
            )
        )
    )
    invalid_filter = False
    category_id = request.GET.get("category")
    if category_id is not None:
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            invalid_filter = True
        else:
            item_list = item_list.filter(category_id=category_id)
    manufacturer_id = request.GET.get("manufacturer")
    if manufacturer_id is not None:
        try:
            manufacturer_id = int(manufacturer_id)
        except (TypeError, ValueError):
            invalid_filter = True
        else:
            item_list = item_list.filter(manufacturer_id=manufacturer_id)
    tag_ids = request.GET.getlist("tag")
    if tag_ids:
        parsed_tag_ids = []
        for tag_id in tag_ids:
            try:
                parsed_tag_ids.append(int(tag_id))
            except (TypeError, ValueError):
                invalid_filter = True
                break
        if not invalid_filter:
            for tag_id in parsed_tag_ids:
                item_list = item_list.filter(tags__id=tag_id)
            item_list = item_list.distinct()
    if invalid_filter:
        item_list = item_list.none()
    context = {"item_list": item_list, "collection": collection}
    return render(request, "partvault/items.html", context)


def collections(request):
    if request.user.is_authenticated:
        my_collections = Collection.objects.filter(owner=request.user)
        public_collections = Collection.objects.filter(is_public=True).exclude(
            owner=request.user
        )
    else:
        my_collections = Collection.objects.none()
        public_collections = Collection.objects.filter(is_public=True)
    context = {
        "my_collections": my_collections,
        "public_collections": public_collections,
    }
    return render(request, "partvault/collections.html", context)


def item(request, item_id):
    grandchild_queryset = (
        Item.objects.select_related("category")
        .prefetch_related(
            Prefetch(
                "photo_set",
                queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
                to_attr="ordered_photos",
            )
        )
        .order_by("name")
    )
    child_queryset = (
        Item.objects.select_related("category")
        .prefetch_related(
            Prefetch(
                "contained_items",
                queryset=grandchild_queryset,
                to_attr="ordered_children",
            ),
            Prefetch(
                "photo_set",
                queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
                to_attr="ordered_photos",
            ),
        )
        .order_by("name")
    )
    item_queryset = Item.objects.select_related(
        "category",
        "collection",
        "manufacturer",
        "parent_item",
        "parent_item__category",
        "status",
    ).prefetch_related(
        "tags",
        Prefetch(
            "contained_items",
            queryset=child_queryset,
            to_attr="ordered_children",
        ),
        Prefetch(
            "photo_set",
            queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
            to_attr="ordered_photos",
        ),
        Prefetch(
            "parent_item__photo_set",
            queryset=Photo.objects.order_by("-is_thumbnail", "-uploaded_at"),
            to_attr="ordered_photos",
        ),
    )
    if not request.user.is_authenticated:
        item_queryset = item_queryset.filter(collection__is_public=True)
    item = get_object_or_404(item_queryset, pk=item_id)
    description_parts = []
    if item.category:
        description_parts.append(str(item.category))
    if item.manufacturer:
        description_parts.append(str(item.manufacturer))
    model_name = (item.model or "").strip()
    if model_name:
        description_parts.append(model_name)
    tags = [str(tag) for tag in item.tags.all()]
    if tags:
        description_parts.append(", ".join(tags))
    description = " · ".join(description_parts)
    og_image_url = None
    photo = item.ordered_photos[0] if item.ordered_photos else None
    if photo and photo.image:
        og_image_url = request.build_absolute_uri(
            reverse("photo_image_scaled", args=[photo.id, 1200])
        )
    context = {
        "item": item,
        "og_title": item.name or "Item",
        "og_description": description,
        "og_url": request.build_absolute_uri(),
        "og_image_url": og_image_url,
    }
    return render(request, "partvault/item_detail.html", context)


def item_by_asset_tag(request, asset_tag):
    item_queryset = Item.objects.all()
    if not request.user.is_authenticated:
        item_queryset = item_queryset.filter(collection__is_public=True)
    normalized_tag = asset_tag.strip().upper()
    item = get_object_or_404(item_queryset, asset_tag=normalized_tag)
    return redirect("item", item_id=item.id)


def _build_item_formsets(post_data=None):
    CategoryFormSet = formset_factory(CategoryForm, extra=1)
    ManufacturerFormSet = formset_factory(ManufacturerForm, extra=1)
    StatusFormSet = formset_factory(StatusForm, extra=1)
    TagFormSet = formset_factory(TagForm, extra=2)
    return {
        "category_formset": CategoryFormSet(post_data, prefix="category"),
        "manufacturer_formset": ManufacturerFormSet(post_data, prefix="manufacturer"),
        "status_formset": StatusFormSet(post_data, prefix="status"),
        "tag_formset": TagFormSet(post_data, prefix="tag"),
    }


def _save_user_inline_objects(formset, model, user):
    created = []
    for form in formset:
        if not form.cleaned_data:
            continue
        name = form.cleaned_data.get("name", "").strip()
        if not name:
            continue
        defaults = {}
        if "color" in form.cleaned_data and form.cleaned_data.get("color"):
            defaults["color"] = form.cleaned_data["color"]
        obj, _ = model.objects.get_or_create(user=user, name=name, defaults=defaults)
        created.append(obj)
    return created


def _build_related_formsets(item=None, post_data=None, files=None, user=None):
    if item is None:
        item = Item()
    PhotoFormSet = inlineformset_factory(
        Item, Photo, form=PhotoForm, extra=3, can_delete=True
    )
    DocumentFormSet = inlineformset_factory(
        Item, Document, form=DocumentForm, extra=2, can_delete=True
    )
    LinkFormSet = inlineformset_factory(
        Item, Link, form=LinkForm, extra=2, can_delete=True
    )
    return {
        "photo_formset": PhotoFormSet(post_data, files, instance=item, prefix="photo"),
        "document_formset": DocumentFormSet(
            post_data,
            files,
            instance=item,
            prefix="document",
            form_kwargs={"user": user},
        ),
        "link_formset": LinkFormSet(
            post_data,
            files,
            instance=item,
            prefix="link",
            form_kwargs={"user": user},
        ),
    }


def _build_user_related_formsets(user, post_data=None):
    CategoryFormSet = modelformset_factory(
        Category, form=CategoryForm, extra=2, can_delete=True
    )
    ManufacturerFormSet = modelformset_factory(
        Manufacturer, form=ManufacturerForm, extra=2, can_delete=True
    )
    StatusFormSet = modelformset_factory(
        Status, form=StatusForm, extra=2, can_delete=True
    )
    TagFormSet = modelformset_factory(Tag, form=TagForm, extra=3, can_delete=True)
    return {
        "category_formset": CategoryFormSet(
            post_data,
            queryset=Category.objects.filter(user=user),
            prefix="category",
        ),
        "manufacturer_formset": ManufacturerFormSet(
            post_data,
            queryset=Manufacturer.objects.filter(user=user),
            prefix="manufacturer",
        ),
        "status_formset": StatusFormSet(
            post_data,
            queryset=Status.objects.filter(user=user),
            prefix="status",
        ),
        "tag_formset": TagFormSet(
            post_data,
            queryset=Tag.objects.filter(user=user),
            prefix="tag",
        ),
    }


def _save_user_formset(formset, user):
    instances = formset.save(commit=False)
    for instance in instances:
        instance.user = user
        instance.save()
    for instance in formset.deleted_objects:
        instance.delete()


def _save_document_formset(formset, user):
    instances = formset.save(commit=False)
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        new_type = form.cleaned_data.get("new_document_type")
        if new_type:
            document_type, _ = LinkType.objects.get_or_create(user=user, name=new_type)
            form.instance.document_type = document_type

    for instance in instances:
        instance.save()

    for instance in formset.deleted_objects:
        instance.delete()


def _save_link_formset(formset, user):
    instances = formset.save(commit=False)
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        new_type = form.cleaned_data.get("new_link_type")
        if new_type:
            link_type, _ = LinkType.objects.get_or_create(
                user=user, name=new_type
            )
            form.instance.link_type = link_type

    for instance in instances:
        instance.save()

    for instance in formset.deleted_objects:
        instance.delete()


@login_required
def item_create(request):
    formsets = _build_item_formsets(
        post_data=request.POST if request.method == "POST" else None
    )
    related_formsets = _build_related_formsets(
        post_data=request.POST if request.method == "POST" else None,
        files=request.FILES if request.method == "POST" else None,
        user=request.user,
    )
    if request.method == "POST":
        form = ItemForm(request.POST, user=request.user)
        formsets_valid = all(formset.is_valid() for formset in formsets.values())
        related_valid = all(formset.is_valid() for formset in related_formsets.values())
        if form.is_valid() and formsets_valid and related_valid:
            collection = form.cleaned_data["collection"]
            if collection.owner != request.user:
                form.add_error("collection", "Select a collection you own.")
            else:
                item = form.save(commit=False)
                item.save()
                form.save_m2m()
                related_formsets["photo_formset"].instance = item
                related_formsets["photo_formset"].save()
                related_formsets["document_formset"].instance = item
                _save_document_formset(related_formsets["document_formset"], request.user)
                related_formsets["link_formset"].instance = item
                _save_link_formset(related_formsets["link_formset"], request.user)
                new_categories = _save_user_inline_objects(
                    formsets["category_formset"], Category, collection.owner
                )
                new_manufacturers = _save_user_inline_objects(
                    formsets["manufacturer_formset"], Manufacturer, collection.owner
                )
                new_statuses = _save_user_inline_objects(
                    formsets["status_formset"], Status, collection.owner
                )
                new_tags = _save_user_inline_objects(
                    formsets["tag_formset"], Tag, collection.owner
                )
                if not item.category and new_categories:
                    item.category = new_categories[0]
                if not item.manufacturer and new_manufacturers:
                    item.manufacturer = new_manufacturers[0]
                if not item.status and new_statuses:
                    item.status = new_statuses[0]
                if new_tags:
                    item.tags.add(*new_tags)
                item.save(update_fields=["category", "manufacturer", "status"])
                messages.success(request, "Item created.")
                return redirect("item", item_id=item.id)
    else:
        active_collection = request.user.profile.active_collection
        initial = {"collection": active_collection} if active_collection else None
        form = ItemForm(
            user=request.user,
            initial=initial,
            collection=active_collection,
        )
    context = {
        "form": form,
        "is_edit": False,
        **formsets,
        **related_formsets,
    }
    return render(request, "partvault/item_form.html", context)


@login_required
def item_edit(request, item_id):
    item = get_object_or_404(Item, pk=item_id, collection__owner=request.user)
    formsets = _build_item_formsets(
        post_data=request.POST if request.method == "POST" else None
    )
    related_formsets = _build_related_formsets(
        item=item,
        post_data=request.POST if request.method == "POST" else None,
        files=request.FILES if request.method == "POST" else None,
        user=request.user,
    )
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item, user=request.user)
        formsets_valid = all(formset.is_valid() for formset in formsets.values())
        related_valid = all(formset.is_valid() for formset in related_formsets.values())
        if form.is_valid() and formsets_valid and related_valid:
            collection = form.cleaned_data["collection"]
            if collection.owner != request.user:
                form.add_error("collection", "Select a collection you own.")
            else:
                item = form.save(commit=False)
                item.save()
                form.save_m2m()
                related_formsets["photo_formset"].save()
                _save_document_formset(related_formsets["document_formset"], request.user)
                _save_link_formset(related_formsets["link_formset"], request.user)
                new_categories = _save_user_inline_objects(
                    formsets["category_formset"], Category, collection.owner
                )
                new_manufacturers = _save_user_inline_objects(
                    formsets["manufacturer_formset"], Manufacturer, collection.owner
                )
                new_statuses = _save_user_inline_objects(
                    formsets["status_formset"], Status, collection.owner
                )
                new_tags = _save_user_inline_objects(
                    formsets["tag_formset"], Tag, collection.owner
                )
                if not item.category and new_categories:
                    item.category = new_categories[0]
                if not item.manufacturer and new_manufacturers:
                    item.manufacturer = new_manufacturers[0]
                if not item.status and new_statuses:
                    item.status = new_statuses[0]
                if new_tags:
                    item.tags.add(*new_tags)
                item.save(update_fields=["category", "manufacturer", "status"])
                messages.success(request, "Item updated.")
                return redirect("item", item_id=item.id)
    else:
        form = ItemForm(instance=item, user=request.user)
    context = {
        "form": form,
        "is_edit": True,
        "item": item,
        **formsets,
        **related_formsets,
    }
    return render(request, "partvault/item_form.html", context)


@login_required
@require_POST
def item_delete(request, item_id):
    item = get_object_or_404(Item, pk=item_id, collection__owner=request.user)
    collection_id = item.collection_id
    item.delete()
    messages.success(request, "Item deleted.")
    return redirect("items", collection_id=collection_id)


def collection(request, collection_id):
    collection_queryset = Collection.objects.all()
    if not request.user.is_authenticated:
        collection_queryset = collection_queryset.filter(is_public=True)
    collection = get_object_or_404(collection_queryset, pk=collection_id)
    return render(
        request,
        "partvault/collection_detail.html",
        {"collection": collection},
    )


@login_required
def collection_create(request):
    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.owner = request.user
            collection.save()
            request.user.profile.active_collection = collection
            request.user.profile.save(update_fields=["active_collection"])
            messages.success(request, "Collection created.")
            return redirect("collection", collection_id=collection.id)
    else:
        form = CollectionForm()
    context = {
        "form": form,
        "is_edit": False,
        "cancel_url": "collections",
    }
    return render(request, "partvault/collection_form.html", context)


@login_required
def collection_edit(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id, owner=request.user)
    if request.method == "POST":
        form = CollectionForm(request.POST, instance=collection)
        if form.is_valid():
            form.save()
            messages.success(request, "Collection updated.")
            return redirect("collection", collection_id=collection.id)
    else:
        form = CollectionForm(instance=collection)
    context = {
        "form": form,
        "is_edit": True,
        "collection": collection,
        "cancel_url": "collection",
    }
    return render(request, "partvault/collection_form.html", context)


@login_required
@require_POST
def collection_delete(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id, owner=request.user)
    collection.delete()
    messages.success(request, "Collection deleted.")
    return redirect("collections")


@login_required
@require_POST
def collection_activate(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id, owner=request.user)
    request.user.profile.active_collection = collection
    request.user.profile.save(update_fields=["active_collection"])
    messages.success(request, "Active collection updated.")
    return redirect("collections")


def profile(request):
    profile = None
    reserved_asset_tag_labels = []
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except ObjectDoesNotExist:
            profile = None
        reserved_asset_tags = list(
            AssetTagSequence.objects.filter(
                reserved_by=request.user,
                status=AssetTagSequence.Status.RESERVED,
            ).values_list("asset_tag", flat=True)
        )
        normalized_tags = [
            asset_tag.strip().upper() for asset_tag in reserved_asset_tags if asset_tag
        ]
        sorted_values = sorted(_base36_to_int(tag) for tag in normalized_tags)
        if sorted_values:
            start = sorted_values[0]
            end = sorted_values[0]
            ranges = []
            for value in sorted_values[1:]:
                if value == end + 1:
                    end = value
                    continue
                ranges.append((start, end))
                start = value
                end = value
            ranges.append((start, end))

            for range_start, range_end in ranges:
                start_tag = _int_to_base36(range_start).zfill(6)
                end_tag = _int_to_base36(range_end).zfill(6)
                count = range_end - range_start + 1
                if range_start == range_end:
                    label = start_tag
                else:
                    label = f"{start_tag} - {end_tag}"
                reserved_asset_tag_labels.append({"label": label, "count": count})
    return render(
        request,
        "partvault/profile.html",
        {
            "profile": profile,
            "reserved_asset_tags": reserved_asset_tag_labels,
        },
    )


@login_required
@require_POST
def reserve_asset_tags(request):
    reserved_count = 0
    for _ in range(250):
        try:
            AssetTagSequence.reserve(request.user)
            reserved_count += 1
        except ValueError:
            break

    if reserved_count == 250:
        messages.success(request, "Reserved 250 asset tags.")
    elif reserved_count:
        messages.warning(
            request,
            (
                f"Reserved {reserved_count} asset tags. "
                "You have reached the 1000 reserved limit."
            ),
        )
    else:
        messages.warning(request, "You already have 1000 reserved asset tags.")
    return redirect("profile")


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        user_formsets = _build_user_related_formsets(
            request.user, post_data=request.POST if action == "item_defaults" else None
        )
        if action == "details":
            profile_form = ProfileForm(request.POST, instance=profile)
            user_form = UserProfileForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
            if profile_form.is_valid() and user_form.is_valid():
                profile_form.save()
                user_form.save()
                messages.success(request, "Profile details updated.")
                return redirect("profile")
        elif action == "password":
            password_form = PasswordChangeForm(request.user, request.POST)
            profile_form = ProfileForm(instance=profile)
            user_form = UserProfileForm(instance=request.user)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated.")
                return redirect("profile")
        elif action == "item_defaults":
            profile_form = ProfileForm(instance=profile)
            user_form = UserProfileForm(instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
            if all(formset.is_valid() for formset in user_formsets.values()):
                for formset in user_formsets.values():
                    _save_user_formset(formset, request.user)
                messages.success(request, "Item defaults updated.")
                return redirect("profile_edit")
        else:
            profile_form = ProfileForm(instance=profile)
            user_form = UserProfileForm(instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
    else:
        user_formsets = _build_user_related_formsets(request.user)
        profile_form = ProfileForm(instance=profile)
        user_form = UserProfileForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
    context = {
        "profile_form": profile_form,
        "user_form": user_form,
        "password_form": password_form,
        **user_formsets,
    }
    return render(request, "partvault/profile_edit.html", context)


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Welcome to PartVault.")
            return redirect("index")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})
