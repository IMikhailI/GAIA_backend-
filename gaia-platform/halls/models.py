from django.db import models


class Hall(models.Model):
    name = models.CharField(max_length=100)  # "Малый зал", "Большой зал"
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    base_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)

    # например, для отображения красивых фоток залов
    photo = models.ImageField(upload_to="halls", blank=True, null=True)

    def __str__(self):
        return self.name


class BlockedSlot(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="blocked_slots")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hall.name}: {self.start_time} - {self.end_time}"
