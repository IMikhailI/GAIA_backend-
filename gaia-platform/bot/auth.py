from typing import Optional

from notifications.models import TelegramAdmin


def get_admin(user_id: int) -> Optional[TelegramAdmin]:
    try:
        return TelegramAdmin.objects.get(telegram_user_id=user_id, is_active=True)
    except TelegramAdmin.DoesNotExist:
        return None


def is_admin(user_id: int) -> bool:
    return get_admin(user_id) is not None


def is_superadmin(user_id: int) -> bool:
    admin = get_admin(user_id)
    return bool(admin and admin.is_superadmin)
