from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "hall",
        "start_time",
        "end_time",
        "customer_name",
        "status",
        "total_price",
    )
    list_filter = ("hall", "status", "start_time")
    search_fields = ("customer_name", "customer_phone", "customer_email")
