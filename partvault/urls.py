from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("image/<int:photo_id>/", views.photo_image, name="photo_image"),
    path(
        "image/<int:photo_id>/<int:long_edge>/",
        views.photo_image,
        name="photo_image_scaled",
    ),
    path("items/<int:collection_id>/", views.items, name="items"),
    path("items/new/", views.item_create, name="item_create"),
    path("items/<int:item_id>/edit/", views.item_edit, name="item_edit"),
    path("items/<int:item_id>/delete/", views.item_delete, name="item_delete"),
    path("collections/", views.collections, name="collections"),
    path("collections/new/", views.collection_create, name="collection_create"),
    path(
        "collections/<int:collection_id>/activate/",
        views.collection_activate,
        name="collection_activate",
    ),
    path(
        "collections/<int:collection_id>/edit/",
        views.collection_edit,
        name="collection_edit",
    ),
    path(
        "collections/<int:collection_id>/delete/",
        views.collection_delete,
        name="collection_delete",
    ),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path(
        "profile/reserve-asset-tags/",
        views.reserve_asset_tags,
        name="reserve_asset_tags",
    ),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("a/<str:asset_tag>/", views.item_by_asset_tag, name="item_by_asset_tag"),
    path("item/<int:item_id>/", views.item, name="item"),
    path("collection/<int:collection_id>/", views.collection, name="collection"),
]
