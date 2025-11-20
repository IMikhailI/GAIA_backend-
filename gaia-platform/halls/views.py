from datetime import date as date_class

from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date

from .models import Hall
from .services import get_available_slots


def halls_list(request):
    halls = Hall.objects.all()
    return render(request, "halls/halls_list.html", {"halls": halls})


def hall_detail(request, slug):
    hall = get_object_or_404(Hall, slug=slug)

    # Дата берётся из GET-параметра ?date=YYYY-MM-DD, по умолчанию — сегодня
    date_str = request.GET.get("date")
    if date_str:
        selected_date = parse_date(date_str)
    else:
        selected_date = date_class.today()

    available_slots = get_available_slots(hall, selected_date)

    context = {
        "hall": hall,
        "selected_date": selected_date,
        "available_slots": available_slots,
    }
    return render(request, "halls/hall_detail.html", context)
