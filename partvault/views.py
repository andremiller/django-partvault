from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Item, Collection


def index(request):
    return render(request, "partvault/index.html")


def items(request):
    item_list = Item.objects.all()
    context = {"item_list": item_list}
    return render(request, "partvault/items.html", context)


def collections(request):
    collection_list = Collection.objects.all()
    context = {"collection_list": collection_list}
    return render(request, "partvault/collections.html", context)


def item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    return render(request, "partvault/item_detail.html", {"item": item})


def collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    return render(
        request,
        "partvault/collection_detail.html",
        {"collection": collection},
    )
