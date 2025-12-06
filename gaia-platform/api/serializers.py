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
            "base_price_per_hour",
            "description",
            "photo",
        ]


class BookingSerializer(serializers.ModelSerializer):
    hall_id = serializers.PrimaryKeyRelatedField(
        queryset=Hall.objects.all(),
        source="hall",
        write_only=True,
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "hall",
            "hall_id",
            "start_time",
            "end_time",
            "customer_name",
            "customer_phone",
            "comment",
            "status",
            "total_price",
        ]
        read_only_fields = ["status", "total_price", "hall"]

    def validate(self, attrs):
        """
        Общая валидация:
        - есть ли зал
        - start < end
        - слот свободен
        """
        hall = attrs.get("hall")
        date = attrs.get("date")
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if not all([hall, date, start_time, end_time]):
            raise serializers.ValidationError(
                "hall_id, date, start_time, end_time обязательны"
            )

        if start_time >= end_time:
            raise serializers.ValidationError(
                "Время начала должно быть меньше времени окончания"
            )

        # Проверяем доступность через booking.services
        if not booking_services.is_slot_available(
            hall=hall,
            date=date,
            start_time=start_time,
            end_time=end_time,
        ):
            raise serializers.ValidationError(
                "Выбранный временной диапазон уже занят или заблокирован"
            )

        return attrs

    def create(self, validated_data):
        """
        Создание брони:
        - выставляем статус
        - считаем цену
        - отправляем уведомления
        """
        hall = validated_data["hall"]
        date = validated_data["date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        # расчёт цены
        total_price = booking_services.calculate_total_price(
            hall=hall,
            date=date,
            start_time=start_time,
            end_time=end_time,
        )

        booking = Booking.objects.create(
            status="new",  # или Booking.STATUS_NEW / Booking.Status.NEW — как у тебя в модели
            total_price=total_price,
            **validated_data,
        )

        # Уведомления (если у тебя в notifications.services уже есть что-то похожее —
        # просто вызови его)
        try:
            notification_services.send_booking_created_notifications(booking)
        except Exception:
            # В проде можно залогировать, но не валить создание брони из-за падения email
            pass

        return booking


class AdminBookingActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class BlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSlot
        fields = [
            "id",
            "hall",
            "start_time",
            "end_time",
            "reason",
        ]
