from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rating", "is_published", "sort_order", "created_at")
    list_filter = ("is_published", "rating", "created_at")
    search_fields = ("name", "text")
    ordering = ("sort_order", "-created_at")

