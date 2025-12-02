from django.urls import path
from .views import MenuFileListAPIView, menu_preview

app_name = "menus"

urlpatterns = [
    path("menu/", MenuFileListAPIView.as_view(), name="menu-list"),
    # HTML-страница для просмотра меню
    path("menu-preview/", menu_preview, name="menu-preview"),
]
