from rest_framework import serializers
from .models import MenuFile


class MenuFileSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = MenuFile
        fields = [
            "id",
            "title",
            "file_url",
            "sort_order",
        ]
