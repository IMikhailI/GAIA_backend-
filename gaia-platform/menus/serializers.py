# menus/serializers.py

from rest_framework import serializers
from .models import MenuFile, MenuPage


class MenuPageSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(source="image", read_only=True)

    class Meta:
        model = MenuPage
        fields = [
            "id",
            "page_number",
            "image_url",
        ]


class MenuFileSerializer(serializers.ModelSerializer):
    pages = MenuPageSerializer(many=True, read_only=True)
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = MenuFile
        fields = [
            "id",
            "title",
            "file_url",   # можно оставить, если нужен PDF
            "sort_order",
            "pages",      # тут лежит массив PNG-страниц
        ]

