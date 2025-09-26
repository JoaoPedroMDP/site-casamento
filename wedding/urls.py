from django.urls import include, path

from wedding import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('galeria', views.GalleryView.as_view(), name='gallery'),
]