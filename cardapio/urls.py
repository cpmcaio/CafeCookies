from django.urls import path
from . import views

app_name = "cardapio"

urlpatterns = [
    path("landing", views.landing, name="landing"),
]
