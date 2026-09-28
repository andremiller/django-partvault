"""Owner-only collection spreadsheet endpoints."""

import logging

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods

from .models import Collection
from .spreadsheets import SpreadsheetError, limits, process_workbook, workbook_bytes

logger = logging.getLogger(__name__)


class SpreadsheetUploadForm(forms.Form):
    workbook = forms.FileField(
        label="Excel workbook",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )
    action = forms.ChoiceField(
        choices=[("preview", "Preview changes"), ("import", "Import now")],
        required=False,
    )


def owned_collection(request, collection_id):
    return get_object_or_404(Collection, pk=collection_id, owner=request.user)


def download(request, collection_id, *, template):
    collection = owned_collection(request, collection_id)
    response = HttpResponse(
        workbook_bytes(collection, template=template),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    suffix = "template" if template else "items"
    response["Content-Disposition"] = (
        f'attachment; filename="collection-{collection.pk}-{suffix}.xlsx"'
    )
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_GET
def spreadsheet_template(request, collection_id):
    return download(request, collection_id, template=True)


@login_required
@require_GET
def spreadsheet_export(request, collection_id):
    return download(request, collection_id, template=False)


@login_required
@require_http_methods(["GET", "POST"])
def spreadsheet_import(request, collection_id):
    collection = owned_collection(request, collection_id)
    form = SpreadsheetUploadForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        commit = form.cleaned_data["action"] == "import"
        try:
            plan = process_workbook(
                collection, request.user, form.cleaned_data["workbook"], commit=commit
            )
        except SpreadsheetError as exc:
            form.add_error("workbook", str(exc))
        except DatabaseError, ValueError:
            logger.exception(
                "Spreadsheet processing failed for collection %s", collection.pk
            )
            form.add_error(
                None,
                "The workbook could not be processed. No changes were saved. Please upload it again.",
            )
        else:
            result_rows = []
            for row in plan["rows"]:
                if row["action"] == "unchanged" and not row["errors"]:
                    continue
                changes = row["changes"]
                if row["action"] == "create":
                    changes = [change for change in changes if change["after"].strip()]
                result_rows.append({**row, "changes": changes})
            response = render(
                request,
                "partvault/spreadsheet_preview.html",
                {
                    "collection": collection,
                    "plan": plan,
                    "result_rows": result_rows,
                    "import_attempted": commit,
                    "import_complete": commit and not plan["counts"]["errors"],
                },
            )
            response["Cache-Control"] = "private, no-store"
            return response
    max_bytes, max_rows = limits()
    return render(
        request,
        "partvault/spreadsheet_upload.html",
        {
            "collection": collection,
            "form": form,
            "max_mib": max_bytes // (1024 * 1024),
            "max_rows": max_rows,
        },
    )
