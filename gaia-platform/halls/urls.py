from django.urls import path
from . import views

app_name = "halls"

urlpatterns = [
    path("", views.halls_list, name="list"),
    path("<slug:slug>/", views.hall_detail, name="detail"),
]
