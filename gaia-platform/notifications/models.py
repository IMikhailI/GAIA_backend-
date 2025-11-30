from django.db import models


class TelegramAdmin(models.Model):
    telegram_user_id = models.BigIntegerField("Telegram ID", unique=True)
    full_name = models.CharField("Имя", max_length=150, blank=True)

    telegram_username = models.CharField("Username", max_length=64, blank=True)

    is_superadmin = models.BooleanField("Суперадмин (владелец)", default=False)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Telegram админ"
        verbose_name_plural = "Telegram админы"
        ordering = ["-is_superadmin", "full_name", "telegram_user_id"]

    def __str__(self):
        prefix = "⭐ " if self.is_superadmin else ""
        name = self.full_name or str(self.telegram_user_id)
        return f"{prefix}{name}"
