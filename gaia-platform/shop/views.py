from rest_framework import generics
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import ProductCategory, Product
from .serializers import ProductCategorySerializer, ProductSerializer


class ProductCategoryListAPIView(generics.ListAPIView):
    """
    GET /api/product-categories/
    """
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer


class ProductListAPIView(generics.ListAPIView):
    """
    GET /api/products/
    ?category=<slug>  — фильтр по категории
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "price", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug, category__is_active=True)
        return qs


class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/products/<id>/
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
