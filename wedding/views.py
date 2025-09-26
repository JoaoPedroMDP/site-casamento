from django.shortcuts import render
from django.views import View

from wedding.models import Photo

class HomeView(View):
    def get(self, request):

        return render(request, 'wedding/home.html')

class GalleryView(View):
    def get(self, request):
        photos = Photo.objects.all()
        return render(request, 'wedding/gallery.html', {'photos': photos})