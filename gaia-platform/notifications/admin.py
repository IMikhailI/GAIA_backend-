from django.contrib import admin
from .models import TelegramAdmin


@admin.register(TelegramAdmin)
class TelegramAdminAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "full_name", "is_superadmin", "is_active", "created_at")
    list_filter = ("is_superadmin", "is_active")
    search_fields = ("telegram_user_id", "full_name")
    list_editable = ("is_superadmin", "is_active")
