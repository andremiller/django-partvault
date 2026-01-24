from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("items/", views.items, name="items"),
    path("collections/", views.collections, name="collections"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("item/<int:item_id>/", views.item, name="item"),
    path("collection/<int:collection_id>/", views.collection, name="collection"),
]
