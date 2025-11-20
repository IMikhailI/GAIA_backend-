from datetime import timedelta

from django.utils import timezone
from django.db.models import Q

from .models import Booking
from halls.models import Hall, BlockedSlot


WORK_DAY_START_HOUR = 9
WORK_DAY_END_HOUR = 21
TIME_SLOT_STEP_HOURS = 1


def is_slot_available(hall: Hall, start_time, duration_hours: int) -> bool:
    """Проверка, что слот свободен и в рабочее время."""
    end_time = start_time + timedelta(hours=duration_hours)

    # проверка на рабочие часы (упрощённо — без учёта выходных и т.п.)
    if start_time.hour < WORK_DAY_START_HOUR:
        return False
    if end_time.hour > WORK_DAY_END_HOUR:
        return False

    # пересечение с другими бронированиями
    overlapping_bookings = Booking.objects.filter(
        hall=hall,
        status__in=["new", "confirmed"],  # учитываем только активные
    ).filter(
        Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
    )

    if overlapping_bookings.exists():
        return False

    # пересечение с блокировками
    overlapping_blocks = BlockedSlot.objects.filter(
        hall=hall,
    ).filter(
        Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
    )

    if overlapping_blocks.exists():
        return False

    return True


def calculate_total_price(hall: Hall, duration_hours: int):
    """Простейший вариант: цена = базовая * часы."""
    return hall.base_price_per_hour * duration_hours
