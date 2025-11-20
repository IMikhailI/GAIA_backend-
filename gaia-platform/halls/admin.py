from django.contrib import admin
from .models import Hall, BlockedSlot


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "base_price_per_hour")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display = ("hall", "start_time", "end_time", "reason")
    list_filter = ("hall", "start_time")
