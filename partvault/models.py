from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Collection(models.Model):
    """A collection of items"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    asset_tag_prefix = models.CharField(max_length=2)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Item(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

    def __str__(self):
        return self.name
    

    
    
