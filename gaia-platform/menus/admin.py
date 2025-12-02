from django.contrib import admin
from .models import MenuFile


@admin.register(MenuFile)
class MenuFileAdmin(admin.ModelAdmin):
    list_display = ("title", "file", "sort_order", "is_active", "created_at")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
