from django.contrib import admin

from .models import (
    AssetTagSequence,
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


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0


class LinkInline(admin.TabularInline):
    model = Link
    extra = 0


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    inlines = [PhotoInline, DocumentInline, LinkInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    list_select_related = ["user"]


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    list_select_related = ["user"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    list_select_related = ["user"]


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "color"]
    list_select_related = ["user"]


admin.site.register(AssetTagSequence)
admin.site.register(Collection)
admin.site.register(DocumentType)
admin.site.register(Document)
admin.site.register(LinkType)
admin.site.register(Link)
admin.site.register(Photo)
admin.site.register(Profile)
