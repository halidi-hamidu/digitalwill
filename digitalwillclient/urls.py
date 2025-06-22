from django.urls import path
from .import views

app_name = "digitalwillclient"

urlpatterns = [
    path('', views.homeview, name="home")
]