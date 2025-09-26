from django.contrib import admin

from wedding.models import Guest, Photo

admin.site.register([
    Photo, Guest,
])