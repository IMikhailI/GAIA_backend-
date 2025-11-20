from rest_framework import serializers

from halls.models import Hall, BlockedSlot
from booking.models import Booking


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = [
            "id",
            "name",
            "slug",
            "capacity",
            "weekday_price_per_hour",
            "weekend_price_per_hour",
            "description",
            "image",
        ]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "hall",
            "date",
            "start_time",
            "end_time",
            "customer_name",
            "customer_phone",
            "comment",
            "status",
            "total_price",
        ]
        read_only_fields = ["status", "total_price"]

    def validate(self, attrs):
        """
        Тут проверяем:
        - пересечения с другими booking (confirmed)
        - пересечения с BlockedSlot
        - мин. длительность >= 1 час и слоты в диапазоне 09:00–21:00
        """
        # TODO: подключи свои сервисы проверки / расчёта
        # пример:
        # from booking.services import validate_booking_request
        # validate_booking_request(attrs)
        return attrs

    def create(self, validated_data):
        """
        Создание брони:
        - рассчитать total_price
        - статус = pending
        - отправить уведомления
        """
        # TODO: вынести в сервисы реальную логику
        booking = Booking.objects.create(
            status=Booking.Status.PENDING,  # или просто "pending"
            **validated_data,
        )

        # пример:
        # from notifications.services import send_booking_created_notifications
        # send_booking_created_notifications(booking)

        return booking


class AdminBookingActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class BlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSlot
        fields = [
            "id",
            "hall",
            "date",
            "start_time",
            "end_time",
            "reason",
        ]
