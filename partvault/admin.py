from django.contrib import admin

from .models import (
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


admin.site.register(Collection)
admin.site.register(Category)
admin.site.register(Manufacturer)
admin.site.register(Status)
admin.site.register(Tag)
admin.site.register(DocumentType)
admin.site.register(Document)
admin.site.register(LinkType)
admin.site.register(Link)
admin.site.register(Photo)
admin.site.register(Profile)

