from django.urls import path

from .views import (
    HallListAPIView,
    HallAvailabilityAPIView,
    BookingCreateAPIView,
    BookingDetailAPIView,
    AdminBookingConfirmAPIView,
    AdminBookingRejectAPIView,
    AdminBlockCreateAPIView,
)

app_name = "api"

urlpatterns = [
    # Публичные эндпоинты для фронта
    path("halls/", HallListAPIView.as_view(), name="hall-list"),
    path("halls/<int:pk>/availability/", HallAvailabilityAPIView.as_view(), name="hall-availability"),
    path("bookings/", BookingCreateAPIView.as_view(), name="booking-create"),
    path("bookings/<int:pk>/", BookingDetailAPIView.as_view(), name="booking-detail"),

    # Админские (для бота)
    path(
        "admin/bookings/<int:pk>/confirm/",
        AdminBookingConfirmAPIView.as_view(),
        name="admin-booking-confirm",
    ),
    path(
        "admin/bookings/<int:pk>/reject/",
        AdminBookingRejectAPIView.as_view(),
        name="admin-booking-reject",
    ),
    path(
        "admin/blocks/",
        AdminBlockCreateAPIView.as_view(),
        name="admin-block-create",
    ),
]
