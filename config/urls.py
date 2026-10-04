"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from re import escape
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from partvault.views import protected_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("partvault.api.urls")),
    path("", include("partvault.urls")),
]

# External storage/web servers must enforce this policy too; see media-delivery.md.
media_url = urlsplit(settings.MEDIA_URL)
if not media_url.netloc:
    urlpatterns += [
        re_path(
            r"^" + escape(media_url.path.lstrip("/")) + r"(?P<path>.*)$",
            protected_media,
        ),
    ]
