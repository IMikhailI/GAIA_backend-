from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from halls.models import Hall, BlockedSlot
from halls.services import get_available_slots
from booking.models import Booking
from booking.services import (
    WORK_DAY_START_HOUR,
    WORK_DAY_END_HOUR,
    TIME_SLOT_STEP_HOURS,
)
from .serializers import (
    HallSerializer,
    BookingSerializer,
    AdminBookingActionSerializer,
    BlockedSlotSerializer,
)


class HallListAPIView(generics.ListAPIView):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer


class HallAvailabilityAPIView(APIView):
    """
    GET /api/halls/<id>/availability?date=YYYY-MM-DD

    Возвращает все слоты рабочего дня с пометкой:
    - "free"  — слот свободен;
    - "busy"  — слот занят (есть Booking или BlockedSlot).
    """

    def get(self, request, pk: int):
        hall = get_object_or_404(Hall, pk=pk)

        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {"detail": "date query param is required (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Invalid date format, expected YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) Берём список свободных слотов через существующий сервис
        free_slots = get_available_slots(hall, target_date)
        # free_slots — список datetime. Преобразуем в множество строк "HH:MM"
        free_times = {slot.strftime("%H:%M") for slot in free_slots}

        # 2) Строим слоты на весь рабочий день
        slots = []
        hour = WORK_DAY_START_HOUR
        while hour < WORK_DAY_END_HOUR:
            slot_time = time(hour=hour, minute=0)
            time_str = slot_time.strftime("%H:%M")
            status_str = "free" if time_str in free_times else "busy"

            slots.append(
                {
                    "time": time_str,
                    "status": status_str,
                }
            )
            hour += TIME_SLOT_STEP_HOURS  # обычно 1 час

        data = {
            "hall_id": hall.id,
            "date": target_date.isoformat(),
            "slots": slots,
        }
        return Response(data)


class BookingCreateAPIView(generics.CreateAPIView):
    """
    POST /api/bookings
    """

    serializer_class = BookingSerializer
    queryset = Booking.objects.all()


class BookingDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/bookings/<id>
    """

    serializer_class = BookingSerializer
    queryset = Booking.objects.all()


# === Админские экшены (для бота) ===


class AdminBookingConfirmAPIView(APIView):
    """
    POST /api/admin/bookings/<id>/confirm
    """

    def post(self, request, pk: int):
        booking = get_object_or_404(Booking, pk=pk)

        # TODO: тут будет проверка, что это админ (по токену/ID и т.п.)

        booking.status = Booking.Status.CONFIRMED  # или "confirmed"
        booking.save(update_fields=["status"])

        # пример: отправка email
        # from notifications.services import send_booking_confirmed_email
        # send_booking_confirmed_email(booking)

        return Response({"id": booking.id, "status": booking.status})


class AdminBookingRejectAPIView(APIView):
    """
    POST /api/admin/bookings/<id>/reject
    body: { "reason": "..." }
    """

    def post(self, request, pk: int):
        booking = get_object_or_404(Booking, pk=pk)
        serializer = AdminBookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("reason", "")

        booking.status = Booking.Status.REJECTED  # или "rejected"
        # Если у тебя есть поле rejection_reason — сохрани туда
        if hasattr(booking, "rejection_reason"):
            booking.rejection_reason = reason
            booking.save(update_fields=["status", "rejection_reason"])
        else:
            booking.save(update_fields=["status"])

        # пример: отправка email
        # from notifications.services import send_booking_rejected_email
        # send_booking_rejected_email(booking, reason=reason)

        return Response(
            {"id": booking.id, "status": booking.status, "reason": reason}
        )


class AdminBlockCreateAPIView(generics.CreateAPIView):
    """
    POST /api/admin/blocks
    """

    serializer_class = BlockedSlotSerializer
    queryset = BlockedSlot.objects.all()
