"""Django-owned shell and generated Vite manifest integration during coexistence."""

import json
import logging
import re
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)
ENTRY_POINT = "src/main.ts"
RESERVED_PATHS = {"api", "admin", "static", "media", "image", "document", "assets"}


def frontend_assets():
    """Return entry scripts and dependency CSS without embedding untrusted HTML."""
    manifest_path = Path(settings.FRONTEND_MANIFEST_PATH)
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError("Invalid frontend manifest")
    styles, preloads, visited = [], [], set()

    def asset_url(filename, suffix):
        if not isinstance(filename, str):
            raise ValueError("Invalid frontend asset")
        path = PurePosixPath(filename)
        if (
            path.is_absolute()
            or ".." in path.parts
            or str(path) != filename
            or path.suffix != suffix
            or not (manifest_path.parent / filename).is_file()
        ):
            raise ValueError("Missing or invalid frontend asset")
        return static(f"partvault/frontend/{filename}")

    def visit(key):
        if key in visited:
            return
        visited.add(key)
        entry = manifest[key]
        if not isinstance(entry, dict):
            raise ValueError("Invalid frontend entry")
        for dependency in entry.get("imports", []):
            visit(dependency)
            url = asset_url(manifest[dependency]["file"], ".js")
            if url not in preloads:
                preloads.append(url)
        for css in entry.get("css", []):
            url = asset_url(css, ".css")
            if url not in styles:
                styles.append(url)

    visit(ENTRY_POINT)
    return {
        "script_url": asset_url(manifest[ENTRY_POINT]["file"], ".js"),
        "style_urls": styles,
        "preload_urls": preloads,
    }


@never_cache
@require_safe
def spa_shell(request, spa_path=""):
    # Only /app/ page routes can use this shell. Assets/API/media never fall back.
    segments = spa_path.split("/")
    if segments[0] in RESERVED_PATHS or any("." in part for part in segments):
        raise Http404("Page not found")
    context = {"app_config": {"siteTitle": settings.SITE_TITLE}}
    try:
        context.update(frontend_assets())
    except OSError, ValueError, KeyError, TypeError, RecursionError:
        logger.warning(
            "Frontend build is missing or invalid; build assets before serving /app/."
        )
        return render(request, "partvault/spa_unavailable.html", context, status=503)
    # Keep known page routes aligned with the Vue router during coexistence.
    known_page = not spa_path or re.fullmatch(
        r"(?:items(?:/(?:[1-9][0-9]*|new))?|item/[1-9][0-9]*(?:/edit)?)/?", spa_path
    )
    return render(
        request, "partvault/spa.html", context, status=200 if known_page else 404
    )
