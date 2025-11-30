from django.apps import AppConfig
from django.conf import settings


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        from .models import TelegramAdmin

        # Если админов нет, создаём начального суперадмина из настроек
        try:
            if not TelegramAdmin.objects.exists():
                chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", 0)
                if chat_id:
                    TelegramAdmin.objects.get_or_create(
                        telegram_user_id=chat_id,
                        defaults={"full_name": "Владелец кофейни", "is_superadmin": True},
                    )
        except Exception:
            # Важно: не ломать загрузку проекта, если что-то пошло не так.
            pass
