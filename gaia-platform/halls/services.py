from datetime import datetime, time, timedelta
from typing import List

from django.utils import timezone

from .models import Hall
from booking.services import (
    WORK_DAY_START_HOUR,
    WORK_DAY_END_HOUR,
    TIME_SLOT_STEP_HOURS,
    is_slot_available,
)


def get_available_slots(hall: Hall, date) -> List[datetime]:
    """
    Возвращает список datetime-слотов (начало часов),
    которые свободны для данного зала в указанную дату.
    """
    slots = []

    for hour in range(WORK_DAY_START_HOUR, WORK_DAY_END_HOUR):
        start_t = time(hour=hour, minute=0)
        start_dt = datetime.combine(date, start_t)

        # если USE_TZ = True, нужно сделать aware:
        # start_dt = timezone.make_aware(start_dt)

        if is_slot_available(hall, start_dt, TIME_SLOT_STEP_HOURS):
            slots.append(start_dt)

    return slots
