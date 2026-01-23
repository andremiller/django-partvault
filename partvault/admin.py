from django.contrib import admin

from .models import Category, Collection, Item, Manufacturer, Status, Tag

admin.site.register(Collection)
admin.site.register(Category)
admin.site.register(Item)
admin.site.register(Manufacturer)
admin.site.register(Status)
admin.site.register(Tag)
