from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("items/", views.items, name="items"),
    path("collections/", views.collections, name="collections"),
    path("item/<int:item_id>/", views.item, name="item"),
    path("collection/<int:collection_id>/", views.collection, name="collection"),
]
