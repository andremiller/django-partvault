from django.urls import path, re_path

from . import views
from .queries import LOOKUPS

app_name = "api-v1"

urlpatterns = [
    path("session/", views.SessionView.as_view(), name="session"),
    path("collections/", views.CollectionListView.as_view(), name="collection-list"),
    path(
        "collections/<int:pk>/",
        views.CollectionDetailView.as_view(),
        name="collection-detail",
    ),
    path(
        "collections/<int:pk>/activate/",
        views.CollectionActivateView.as_view(),
        name="collection-activate",
    ),
    path("items/", views.ItemListView.as_view(), name="item-list"),
    path("items/<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("filter-facets/", views.FilterFacetView.as_view(), name="filter-facets"),
]

for resource in ("children", "photos", "documents", "links"):
    urlpatterns.append(
        path(
            f"items/<int:item_id>/{resource}/",
            views.ItemResourceView.as_view(resource=resource),
            name=f"item-{resource}",
        )
    )
    if resource != "children":
        urlpatterns.append(
            path(
                f"items/<int:item_id>/{resource}/<int:resource_id>/",
                views.ItemResourceView.as_view(resource=resource),
                name=f"item-{resource}-detail",
            )
        )

for lookup in LOOKUPS:
    urlpatterns.append(
        path(
            f"{lookup}/",
            views.LookupListView.as_view(lookup=lookup),
            name=f"{lookup}-list",
        )
    )

    urlpatterns.append(
        path(
            f"{lookup}/<int:pk>/",
            views.LookupDetailView.as_view(lookup=lookup),
            name=f"{lookup}-detail",
        )
    )

# Keep unknown API GETs JSON, including during later SPA route coexistence.
urlpatterns.append(re_path(r"^.*$", views.MissingEndpointView.as_view()))
