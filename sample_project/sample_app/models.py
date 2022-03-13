from django.db import models
from taggit.managers import TaggableManager


class Albums(models.Model):
    album_name = models.CharField(max_length=255)
    band_name = models.CharField(max_length=255)
    tags = TaggableManager()
