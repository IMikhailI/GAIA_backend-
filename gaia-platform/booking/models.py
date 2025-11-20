from django.db import models
from django.utils import timezone
from halls.models import Hall


class Booking(models.Model):
    STATUS_CHOICES = [
        ("new", "Новая"),
        ("confirmed", "Подтверждена"),
        ("cancelled", "Отменена"),
        ("rejected", "Отклонена"),
    ]

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="bookings")

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=50)
    customer_email = models.EmailField()

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_hours = models.PositiveIntegerField()

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new"
    )

    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hall.name} {self.start_time} ({self.customer_name})"

    class Meta:
        ordering = ["-created_at"]
