from django.conf import settings
from django.core.mail import send_mail

from .telegram import send_telegram_message


def send_booking_notifications(booking):
    """
    Уведомления при создании НОВОЙ заявки:
    1) Клиенту — что заявка получена.
    2) Админу — по email.
    3) Админу — в Telegram.
    """

    # 1. Клиенту
    subject_client = "GAIA: ваша заявка на бронирование получена"
    message_client = (
        f"Здравствуйте, {booking.customer_name}!\n\n"
        f"Ваша заявка на бронирование зала «{booking.hall.name}» принята.\n"
        f"Дата и время: {booking.start_time.strftime('%d.%m.%Y %H:%M')} - "
        f"{booking.end_time.strftime('%H:%M')}\n"
        f"Стоимость: {booking.total_price} руб.\n\n"
        "Мы свяжемся с вами для подтверждения."
    )

    send_mail(
        subject_client,
        message_client,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer_email],
        fail_silently=True,
    )

    # 2. Админу по email
    admin_email = getattr(settings, "GAIA_ADMIN_EMAIL", None)
    if admin_email:
        subject_admin = "GAIA: новая заявка на бронирование"
        message_admin = (
            f"Новая заявка на бронирование:\n\n"
            f"Зал: {booking.hall.name}\n"
            f"Клиент: {booking.customer_name}\n"
            f"Телефон: {booking.customer_phone}\n"
            f"Email: {booking.customer_email}\n"
            f"Дата и время: {booking.start_time.strftime('%d.%m.%Y %H:%M')} - "
            f"{booking.end_time.strftime('%H:%M')}\n"
            f"Стоимость: {booking.total_price} руб.\n"
            f"Комментарий: {booking.comment or '—'}\n"
            f"ID брони: {booking.id}\n"
        )

        send_mail(
            subject_admin,
            message_admin,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=True,
        )

     # 3. Администратору в Telegram
    admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)
    if admin_chat_id:
        text = (
            "<b>Новая заявка на бронирование</b> 🔔💰\n\n"
            f"ID: {booking.id}\n"
            f"Зал: {booking.hall.name}\n"
            f"Клиент: {booking.customer_name}\n"
            f"Телефон: {booking.customer_phone}\n"
            f"Email: {booking.customer_email}\n"
            f"Дата и время: {booking.start_time.strftime('%d.%m.%Y %H:%M')} - "
            f"{booking.end_time.strftime('%H:%M')}\n"
            f"Стоимость: {booking.total_price} руб.\n"
            f"Комментарий: {booking.comment or '—'}"
        )
        send_telegram_message(admin_chat_id, text)


def send_booking_status_update_notification(booking):
    """
    Уведомление клиенту о смене статуса: confirmed / cancelled / rejected.
    """
    subject = None
    message = None

    if booking.status == "confirmed":
        subject = "GAIA: ваше бронирование подтверждено"
        message = (
            f"Здравствуйте, {booking.customer_name}!\n\n"
            f"Ваше бронирование зала «{booking.hall.name}» подтверждено.\n"
            f"Дата и время: {booking.start_time.strftime('%d.%m.%Y %H:%M')} - "
            f"{booking.end_time.strftime('%H:%M')}\n"
            f"Стоимость: {booking.total_price} руб.\n\n"
            "До встречи в GAIA!"
        )
    elif booking.status in ("cancelled", "rejected"):
        subject = "GAIA: ваше бронирование отменено"
        message = (
            f"Здравствуйте, {booking.customer_name}!\n\n"
            f"Ваше бронирование зала «{booking.hall.name}» "
            f"на {booking.start_time.strftime('%d.%m.%Y %H:%M')} отменено.\n\n"
            "Если это ошибка, свяжитесь с нами по телефону или через сайт."
        )

    if not (subject and message):
        return

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer_email],
        fail_silently=True,
    )
