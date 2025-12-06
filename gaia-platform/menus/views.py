from rest_framework import generics
from .models import MenuFile
from .serializers import MenuFileSerializer

from django.shortcuts import render


class MenuFileListAPIView(generics.ListAPIView):
    """
    GET /api/menu/ — список активных PDF-страниц меню
    """
    queryset = MenuFile.objects.filter(is_active=True).order_by("sort_order", "created_at")
    serializer_class = MenuFileSerializer

def menu_preview(request):
    menu_files = (
        MenuFile.objects
        .filter(is_active=True)
        .prefetch_related("pages")
        .order_by("sort_order", "created_at")
    )
    return render(request, "menus/menu_preview.html", {"menu_files": menu_files})
