from rest_framework import serializers

from halls.models import Hall, BlockedSlot
from booking.models import Booking
from booking import services as booking_services
from reviews.models import Review
from notifications.services import send_booking_notifications


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
            "duration_hours",
            "customer_name",
            "customer_phone",
            "customer_email",
            "comment",
            "status",
            "total_price",
        ]
        # hall и duration_hours заполняются на бэкенде
        read_only_fields = ["status", "total_price", "hall", "duration_hours"]

    def validate(self, attrs):
        """
        Общая валидация:
        - есть ли зал
        - start < end
        - слот свободен (учитывая Booking и BlockedSlot)
        """
        hall = attrs.get("hall")
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if not all([hall, start_time, end_time]):
            raise serializers.ValidationError(
                "hall_id, start_time, end_time обязательны"
            )

        if start_time >= end_time:
            raise serializers.ValidationError(
                {"end_time": "Время окончания должно быть позже начала"}
            )

        # считаем длительность в часах
        delta_seconds = (end_time - start_time).total_seconds()
        duration_hours = int(delta_seconds // 3600)
        if duration_hours <= 0:
            duration_hours = 1  # минимально 1 час

        # проверяем, что слот свободен
        if not booking_services.is_slot_available(
            hall=hall,
            start_time=start_time,
            duration_hours=duration_hours,
        ):
            raise serializers.ValidationError(
                "Выбранный временной диапазон уже занят или заблокирован"
            )

        # прокидываем duration_hours дальше, чтобы не считать второй раз
        attrs["duration_hours"] = duration_hours
        return attrs

    def create(self, validated_data):
        """
        Создание брони:
        - считаем duration_hours (если по какой-то причине не попало из validate)
        - считаем цену
        - создаём Booking
        - отправляем уведомления (email + телеграм) через единый сервис
        """
        hall = validated_data["hall"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        # duration_hours уже проброшен в validate, но на всякий случай досчитаем
        duration_hours = validated_data.get("duration_hours")
        if duration_hours is None:
            delta_seconds = (end_time - start_time).total_seconds()
            duration_hours = int(delta_seconds // 3600) or 1

        total_price = booking_services.calculate_total_price(
            hall=hall,
            duration_hours=duration_hours,
        )

        booking = Booking.objects.create(
            hall=hall,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            total_price=total_price,
            status="new",
            customer_name=validated_data["customer_name"],
            customer_phone=validated_data["customer_phone"],
            customer_email=validated_data["customer_email"],
            comment=validated_data.get("comment", ""),
        )

        # Уведомления: используем существующий сервис,
        # который уже умеет слать и телеграм, и email.
        try:
            send_booking_notifications(booking)
        except Exception as e:
            # Чтобы не ломать создание брони, ошибки уведомлений
            # глушим, но в режиме DEBUG их имеет смысл логировать.
            from django.conf import settings
            if settings.DEBUG:
                print(f"send_booking_notifications error: {e}")

        return booking



class AdminBookingActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class BlockedSlotSerializer(serializers.ModelSerializer):
    hall_name = serializers.CharField(source="hall.name", read_only=True)

    class Meta:
        model = BlockedSlot
        fields = [
            "id",
            "hall",
            "hall_name",
            "start_time",
            "end_time",
            "reason",
        ]
        read_only_fields = ["id", "hall_name"]


class ReviewSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "name",
            "photo",
            "rating",
            "text",
            "created_at",
        ]

    def get_photo(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            url = obj.avatar.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None
