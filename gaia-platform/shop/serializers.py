from rest_framework import serializers

from .models import ProductCategory, Product


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
        ]


class ProductSerializer(serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.filter(is_active=True),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "image",
            "is_active",
            "category",
            "category_id",
        ]
        read_only_fields = ["is_active"]
