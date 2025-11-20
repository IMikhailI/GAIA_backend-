from django.shortcuts import render
from halls.models import Hall


def home(request):
    halls = Hall.objects.all()
    return render(request, "landing/home.html", {"halls": halls})
