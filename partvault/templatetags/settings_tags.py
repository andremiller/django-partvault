from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def setting(name, default=""):
    return getattr(settings, name, default)
