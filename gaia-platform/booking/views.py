from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from django.utils import timezone  # можно не использовать, если USE_TZ = False

from django.shortcuts import render, redirect
from django.contrib import messages

from halls.models import Hall
from .forms import BookingForm
from .models import Booking
from .services import is_slot_available, calculate_total_price
from notifications.services import send_booking_notifications


def create_booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            hall = form.cleaned_data["hall"]
            start_dt = form.cleaned_data["start_datetime"]
            duration_hours = form.cleaned_data["duration_hours"]

            if not is_slot_available(hall, start_dt, duration_hours):
                messages.error(request, "Выбранный слот уже занят или недоступен.")
            else:
                end_dt = start_dt + timedelta(hours=duration_hours)
                total_price = calculate_total_price(hall, duration_hours)

                booking = Booking.objects.create(
                    hall=hall,
                    customer_name=form.cleaned_data["customer_name"],
                    customer_phone=form.cleaned_data["customer_phone"],
                    customer_email=form.cleaned_data["customer_email"],
                    start_time=start_dt,
                    end_time=end_dt,
                    duration_hours=duration_hours,
                    total_price=total_price,
                    comment=form.cleaned_data.get("comment", ""),
                )

                send_booking_notifications(booking)

                messages.success(
                    request,
                    "Бронирование создано! Мы свяжемся с вами для подтверждения.",
                )
                return redirect("booking:create")
    else:
        # читаем параметры из GET, если пришли с hall_detail
        hall_id = request.GET.get("hall")
        date_str = request.GET.get("date")
        time_str = request.GET.get("time")

        initial = {}

        if hall_id:
            try:
                initial["hall"] = Hall.objects.get(id=hall_id)
            except Hall.DoesNotExist:
                pass

        if date_str:
            initial["date"] = parse_date(date_str)

        if time_str:
            initial["start_time"] = time_str  # строка "HH:MM" подходит ChoiceField

        form = BookingForm(initial=initial)

    return render(request, "booking/create_booking.html", {"form": form})
