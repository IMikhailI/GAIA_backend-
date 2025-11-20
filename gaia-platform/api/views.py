from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from halls.models import Hall, BlockedSlot
from booking.models import Booking
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

        # Старт/конец рабочего дня
        start_hour = 9
        end_hour = 21  # последний слот 20:00–21:00

        # Берём все подтверждённые брони и блокировки на этот день
        bookings = Booking.objects.filter(
            hall=hall,
            date=target_date,
            status=Booking.Status.CONFIRMED,  # или "confirmed"
        )
        blocks = BlockedSlot.objects.filter(
            hall=hall,
            date=target_date,
        )

        def slot_status(slot_time: time) -> str:
            # Проверяем, попадает ли слот в бронь или блокировку
            for b in bookings:
                if b.start_time <= slot_time < b.end_time:
                    return "busy"
            for bl in blocks:
                if bl.start_time <= slot_time < bl.end_time:
                    return "blocked"
            return "free"

        slots = []
        current_dt = datetime.combine(target_date, time(hour=start_hour))
        end_dt = datetime.combine(target_date, time(hour=end_hour))

        while current_dt < end_dt:
            t = current_dt.time()
            slots.append(
                {
                    "time": t.strftime("%H:%M"),
                    "status": slot_status(t),
                }
            )
            current_dt += timedelta(hours=1)

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
