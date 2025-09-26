from django.db import models


class Guest(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    code = models.CharField(max_length=10, unique=True)

class Photo(models.Model):
    image = models.ImageField(upload_to='photos/')
    title = models.CharField(max_length=100)
