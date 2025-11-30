from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from halls.models import Hall, BlockedSlot
from halls.services import get_available_slots
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

        # Берём свободные слоты через сервис
        free_slots = get_available_slots(hall, target_date)
        # Предположим, что free_slots — iterable из datetime/time.
        # Преобразуем в удобный для фронта вид:
        slots = [
            {"time": slot.strftime("%H:%M"), "status": "free"}
            for slot in free_slots
        ]

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
