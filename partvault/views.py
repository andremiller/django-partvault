from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.forms import PasswordChangeForm

from .models import Item, Collection, Profile
from .forms import ProfileForm, UserProfileForm, SignupForm


def index(request):
    return render(request, "partvault/index.html")


def items(request):
    item_list = Item.objects.all()
    if not request.user.is_authenticated:
        item_list = item_list.filter(collection__is_public=True)
    context = {"item_list": item_list}
    return render(request, "partvault/items.html", context)


def collections(request):
    collection_list = Collection.objects.all()
    if not request.user.is_authenticated:
        collection_list = collection_list.filter(is_public=True)
    context = {"collection_list": collection_list}
    return render(request, "partvault/collections.html", context)


def item(request, item_id):
    item_queryset = Item.objects.all()
    if not request.user.is_authenticated:
        item_queryset = item_queryset.filter(collection__is_public=True)
    item = get_object_or_404(item_queryset, pk=item_id)
    return render(request, "partvault/item_detail.html", {"item": item})


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
