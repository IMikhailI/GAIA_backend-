from django.urls import path
from . import views

app_name = "booking"

urlpatterns = [
    path("create/", views.create_booking, name="create"),
]
