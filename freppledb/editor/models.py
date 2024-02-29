from django.db import models

# Create your models here.
class AppRelatedSettings(models.Model):
    name = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    def __string__(self):
        return self.name