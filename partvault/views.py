from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_POST
from django.forms import formset_factory, inlineformset_factory

from .models import (
    Category,
    Collection,
    Document,
    DocumentType,
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


def index(request):
    return render(request, "partvault/index.html")


def items(request):
    item_list = Item.objects.all()
    if not request.user.is_authenticated:
        item_list = item_list.filter(collection__is_public=True)
    context = {"item_list": item_list}
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
    item_queryset = Item.objects.all()
    if not request.user.is_authenticated:
        item_queryset = item_queryset.filter(collection__is_public=True)
    item = get_object_or_404(item_queryset, pk=item_id)
    return render(request, "partvault/item_detail.html", {"item": item})


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


def _save_inline_objects(formset, model, collection):
    created = []
    for form in formset:
        if not form.cleaned_data:
            continue
        name = form.cleaned_data.get("name", "").strip()
        if not name:
            continue
        obj, _ = model.objects.get_or_create(collection=collection, name=name)
        created.append(obj)
    return created


def _build_related_formsets(item=None, post_data=None, files=None):
    if item is None:
        item = Item()
    PhotoFormSet = inlineformset_factory(
        Item, Photo, form=PhotoForm, extra=2, can_delete=True
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
            post_data, files, instance=item, prefix="document"
        ),
        "link_formset": LinkFormSet(post_data, files, instance=item, prefix="link"),
    }


def _save_document_formset(formset, collection):
    instances = formset.save(commit=False)
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        new_type = form.cleaned_data.get("new_document_type")
        if new_type:
            document_type, _ = DocumentType.objects.get_or_create(
                collection=collection, name=new_type
            )
            form.instance.document_type = document_type

    for instance in instances:
        instance.save()

    for instance in formset.deleted_objects:
        instance.delete()


def _save_link_formset(formset, collection):
    instances = formset.save(commit=False)
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        new_type = form.cleaned_data.get("new_link_type")
        if new_type:
            link_type, _ = LinkType.objects.get_or_create(
                collection=collection, name=new_type
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
                _save_document_formset(related_formsets["document_formset"], collection)
                related_formsets["link_formset"].instance = item
                _save_link_formset(related_formsets["link_formset"], collection)
                new_categories = _save_inline_objects(
                    formsets["category_formset"], Category, collection
                )
                new_manufacturers = _save_inline_objects(
                    formsets["manufacturer_formset"], Manufacturer, collection
                )
                new_statuses = _save_inline_objects(
                    formsets["status_formset"], Status, collection
                )
                new_tags = _save_inline_objects(
                    formsets["tag_formset"], Tag, collection
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
                _save_document_formset(related_formsets["document_formset"], collection)
                _save_link_formset(related_formsets["link_formset"], collection)
                new_categories = _save_inline_objects(
                    formsets["category_formset"], Category, collection
                )
                new_manufacturers = _save_inline_objects(
                    formsets["manufacturer_formset"], Manufacturer, collection
                )
                new_statuses = _save_inline_objects(
                    formsets["status_formset"], Status, collection
                )
                new_tags = _save_inline_objects(
                    formsets["tag_formset"], Tag, collection
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
    item.delete()
    messages.success(request, "Item deleted.")
    return redirect("items")


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
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except ObjectDoesNotExist:
            profile = None
    return render(request, "partvault/profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        action = request.POST.get("action")
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
        else:
            profile_form = ProfileForm(instance=profile)
            user_form = UserProfileForm(instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
    else:
        profile_form = ProfileForm(instance=profile)
        user_form = UserProfileForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
    context = {
        "profile_form": profile_form,
        "user_form": user_form,
        "password_form": password_form,
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
