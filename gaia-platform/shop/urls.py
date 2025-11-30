from django.urls import path

from .views import (
    ProductCategoryListAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
)

app_name = "shop"

urlpatterns = [
    path("product-categories/", ProductCategoryListAPIView.as_view(), name="category-list"),
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailAPIView.as_view(), name="product-detail"),
]
