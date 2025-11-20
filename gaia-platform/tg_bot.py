import os
import django
from datetime import date as date_class, timedelta, datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)
from telegram.error import BadRequest

# --- Настройка Django окружения ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gaia.settings")
django.setup()

from django.conf import settings
from booking.models import Booking
from notifications.services import send_booking_status_update_notification

ADMIN_CHAT_ID = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None)


def is_admin_chat(chat_id: int) -> bool:
    return chat_id == ADMIN_CHAT_ID


def is_admin(update) -> bool:
    return is_admin_chat(update.effective_chat.id)


# ---------------- Главное меню ----------------

def get_main_menu():
    keyboard = [
        ["📅 Брони на сегодня", "📅 Брони на завтра"],
        ["🆕 Новые брони", "📈 Все предстоящие брони"],
        ["📆 Выбрать дату"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------- Форматирование текста ----------------

def format_booking_short(b: Booking) -> str:
    return (
        f"ID {b.id}: {b.hall.name}, "
        f"{b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')}, {b.start_time.strftime('%d.%m.%Y')},"
        # f"{b.customer_name}, "
        f"\n<b>Статус: {b.get_status_display()}</b>"
    )


def format_booking_full(b: Booking) -> str:
    return (
        f"ID {b.id}\n"
        f"Зал: {b.hall.name}\n"
        f"Клиент: {b.customer_name}\n"
        f"Телефон: {b.customer_phone}\n"
        f"Email: {b.customer_email}\n"
        f"Время: {b.start_time.strftime('%d.%m.%Y %H:%M')}–{b.end_time.strftime('%H:%M')}\n"
        f"Стоимость: {b.total_price} руб.\n"
        f"<b>Статус: {b.get_status_display()}</b>\n"
        f"Комментарий: {b.comment or '—'}"
    )


def build_booking_keyboard(booking: Booking, expanded: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для одной брони.
    expanded = False  -> кнопка 'Подробнее'
    expanded = True   -> кнопка 'Свернуть'
    """
    if expanded:
        info_text = "↩ Свернуть"
        info_action = "info_short"
    else:
        info_text = "ℹ️ Подробнее"
        info_action = "info_full"

    buttons = [
        [InlineKeyboardButton(info_text, callback_data=f"{info_action}:{booking.id}")]
    ]

    if booking.status == "new":
        buttons[0].append(
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm:{booking.id}")
        )
        buttons[0].append(
            InlineKeyboardButton("❌ Отменить", callback_data=f"cancel:{booking.id}")
        )
    elif booking.status == "confirmed":
        buttons[0].append(
            InlineKeyboardButton("❌ Отменить", callback_data=f"cancel:{booking.id}")
        )
    # cancelled / rejected -> только инфо

    return InlineKeyboardMarkup(buttons)


# ---------------- Базовые команды ----------------

def start(update, context):
    if not is_admin(update):
        update.message.reply_text("У вас нет доступа к админке GAIA.")
        return

    update.message.reply_text(
        "Привет! Это админ-бот GAIA.\n\n"
        "Используй кнопки внизу:\n"
        "• 📅 Брони на сегодня\n"
        "• 📅 Брони на завтра\n"
        "• 🆕 Новые брони\n"
        "• 📈 Все предстоящие брони\n"
        "• 📆 Выбрать дату",
        reply_markup=get_main_menu(),
    )


def ping(update, context):
    if not is_admin(update):
        return
    update.message.reply_text("Pong! Я на связи ✅")


# ---------------- Работа с датами и выборками ----------------

def parse_date_text(text: str):
    """
    Пытаемся распарсить дату из строки.
    Поддерживаем форматы: ДД.ММ.ГГГГ и ГГГГ-ММ-ДД.
    """
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def send_bookings_for_date(update, context, target_date: date_class, label: str):
    """Показать брони на указанную дату."""
    bookings = Booking.objects.filter(start_time__date=target_date).order_by("start_time")

    if not bookings:
        update.message.reply_text(
            f"На {label} броней нет.",
            reply_markup=get_main_menu(),
        )
        return

    update.message.reply_text(
        f"Брони на {label}:",
        reply_markup=get_main_menu(),
    )

    for b in bookings:
        text = format_booking_short(b)
        keyboard = build_booking_keyboard(b, expanded=False)
        update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


def send_new_bookings(update, context):
    """Показать все новые предстоящие брони (статус new, с сегодняшнего дня)."""
    today = date_class.today()
    bookings = (
        Booking.objects
        .filter(start_time__date__gte=today, status="new")
        .order_by("start_time")
    )

    if not bookings:
        update.message.reply_text(
            "Новых предстоящих броней нет.",
            reply_markup=get_main_menu(),
        )
        return

    update.message.reply_text(
        "🆕 Новые предстоящие брони:",
        reply_markup=get_main_menu(),
    )

    for b in bookings:
        text = format_booking_short(b)
        keyboard = build_booking_keyboard(b, expanded=False)
        update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


def send_all_upcoming(update, context):
    """Показать все предстоящие брони (new + confirmed, с сегодняшнего дня)."""
    today = date_class.today()
    bookings = (
        Booking.objects
        .filter(start_time__date__gte=today, status__in=["new", "confirmed"])
        .order_by("start_time")
    )

    if not bookings:
        update.message.reply_text(
            "Предстоящих броней нет.",
            reply_markup=get_main_menu(),
        )
        return

    update.message.reply_text(
        "📈 Все предстоящие брони:",
        reply_markup=get_main_menu(),
    )

    for b in bookings:
        text = format_booking_short(b)
        keyboard = build_booking_keyboard(b, expanded=False)
        update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


# ---------------- Обработка сообщений (меню + ввод даты) ----------------

def handle_menu(update, context):
    """Реагируем на текстовые сообщения: кнопки меню и ввод даты."""
    if not is_admin(update):
        return

    user_data = context.user_data
    text = (update.message.text or "").strip()

    # Режим ожидания ввода даты
    if user_data.get("awaiting_date"):
        target_date = parse_date_text(text)
        if not target_date:
            update.message.reply_text(
                "Не удалось распознать дату.\n"
                "Пожалуйста, введите в формате ДД.ММ.ГГГГ (например, 14.11.2025).",
                reply_markup=get_main_menu(),
            )
            return

        user_data["awaiting_date"] = False
        label = target_date.strftime("%d.%m.%Y")
        send_bookings_for_date(update, context, target_date, label)
        return

    # Нажатия на кнопки меню
    if text.startswith("📅 Брони на сегодня"):
        today = date_class.today()
        label = "сегодня"
        send_bookings_for_date(update, context, today, label)

    elif text.startswith("📅 Брони на завтра"):
        tomorrow = date_class.today() + timedelta(days=1)
        label = "завтра"
        send_bookings_for_date(update, context, tomorrow, label)

    elif text.startswith("🆕 Новые брони"):
        send_new_bookings(update, context)

    elif text.startswith("📈 Все предстоящие брони"):
        send_all_upcoming(update, context)

    elif text.startswith("📆 Выбрать дату"):
        user_data["awaiting_date"] = True
        update.message.reply_text(
            "Введите дату в формате ДД.ММ.ГГГГ (например, 14.11.2025):",
            reply_markup=get_main_menu(),
        )

    else:
        update.message.reply_text(
            "Не понимаю этот ввод. Используй кнопки меню снизу 🙂",
            reply_markup=get_main_menu(),
        )


# ---------------- Обработчик нажатий на inline-кнопки ----------------

def booking_callback(update, context):
    """Обрабатываем нажатия на кнопки ℹ️ / ↩ / ✅ / ❌."""
    query = update.callback_query
    chat_id = query.message.chat_id

    if not is_admin_chat(chat_id):
        query.answer("Нет доступа.")
        return

    data = query.data  # "info_full:10", "info_short:10", "confirm:10", "cancel:10"
    try:
        action, booking_id_str = data.split(":")
        booking_id = int(booking_id_str)
        b = Booking.objects.get(id=booking_id)
    except Exception:
        query.answer("Ошибка: бронь не найдена.")
        return

    if action == "info_full":
        # показать полную информацию + кнопку "Свернуть"
        text = format_booking_full(b)
        keyboard = build_booking_keyboard(b, expanded=True)
        try:
            query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            pass
        query.answer("Показана подробная информация.")

    elif action == "info_short":
        # свернуть обратно в краткий вид + кнопку "Подробнее"
        text = format_booking_short(b)
        keyboard = build_booking_keyboard(b, expanded=False)
        try:
            query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            pass
        query.answer("Свернули до краткой информации.")

    elif action == "confirm":
        if b.status == "confirmed":
            query.answer("Бронь уже подтверждена.")
            return
        if b.status in ("cancelled", "rejected"):
            query.answer("Нельзя подтвердить отменённую/отклонённую бронь.")
            return

        b.status = "confirmed"
        b.save()
        send_booking_status_update_notification(b)

        new_text = format_booking_short(b)
        try:
            # Кнопки убираем после действия
            query.edit_message_text(
                new_text,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            pass

        query.answer("Бронь подтверждена ✅")

    elif action == "cancel":
        if b.status == "cancelled":
            query.answer("Бронь уже отменена.")
            return
        if b.status == "rejected":
            query.answer("Бронь уже отклонена.")
            return

        # Разрешаем отменять "new" и "confirmed"
        b.status = "cancelled"
        b.save()
        send_booking_status_update_notification(b)

        new_text = format_booking_short(b)
        try:
            query.edit_message_text(
                new_text,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            pass

        query.answer("Бронь отменена ❌")

    else:
        query.answer("Неизвестное действие.")


# ---------------- main ----------------

def main():
    token = settings.TELEGRAM_BOT_TOKEN
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # Команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ping", ping))

    # Все текстовые сообщения (не команды) — работа с меню и вводом даты
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_menu))

    # Инлайн-кнопки под бронированием
    dp.add_handler(CallbackQueryHandler(booking_callback))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
