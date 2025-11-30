import os
import django
import html
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
from notifications.models import TelegramAdmin


# ---------------- Роли и помощники авторизации ----------------


def get_admin(user_id: int) -> TelegramAdmin | None:
    try:
        return TelegramAdmin.objects.get(telegram_user_id=user_id, is_active=True)
    except TelegramAdmin.DoesNotExist:
        return None


def is_admin(user_id: int) -> bool:
    return get_admin(user_id) is not None


def is_superadmin(user_id: int) -> bool:
    admin = get_admin(user_id)
    return bool(admin and admin.is_superadmin)


# ---------------- Главное меню ----------------


def get_main_menu(is_superadmin_flag: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        ["📅 Брони на сегодня", "📅 Брони на завтра"],
        ["🆕 Новые брони", "📈 Все предстоящие брони"],
        ["📆 Выбрать дату"],
    ]

    # Для владельца добавляем ряд с командами управления персоналом
    if is_superadmin_flag:
        keyboard.append(["/staff_list", "/remove_staff"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------- Форматирование текста по брони ----------------


def format_booking_short(b: Booking) -> str:
    return (
        f"ID {b.id}: {b.hall.name}, "
        f"{b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')}, "
        f"{b.start_time.strftime('%d.%m.%Y')}\n"
        f"<b>Статус: {b.get_status_display()}</b>"
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


# ---------------- Уведомление суперадмина о запросе доступа ----------------


def notify_superadmins_about_access_request(user, context):
    """Уведомить суперадминов, что пользователь просит доступ к боту.

    Тут же создаём/обновляем запись TelegramAdmin с full_name и username,
    но не активируем (is_active остаётся False до одобрения).
    """
    admin_obj, created = TelegramAdmin.objects.get_or_create(
        telegram_user_id=user.id,
        defaults={
            "full_name": user.full_name or "",
            "telegram_username": user.username or "",
            "is_superadmin": False,
            "is_active": False,
        },
    )
    if not created:
        updated = False
        new_full_name = user.full_name or ""
        new_username = user.username or ""
        if admin_obj.full_name != new_full_name:
            admin_obj.full_name = new_full_name
            updated = True
        if admin_obj.telegram_username != new_username:
            admin_obj.telegram_username = new_username
            updated = True
        if updated:
            admin_obj.save(update_fields=["full_name", "telegram_username"])

    admins = TelegramAdmin.objects.filter(is_superadmin=True, is_active=True)
    if not admins.exists():
        return

    for admin in admins:
        full_name = html.escape(user.full_name or "—")
        username_shown = f"@{user.username}" if user.username else "—"

        text = (
            "Запрос на доступ к админ-боту GAIA:\n\n"
            f"Имя: {full_name}\n"
            f"Username: {html.escape(username_shown)}\n"
            f"ID: <code>{user.id}</code>\n\n"
            "Нажмите кнопку ниже, чтобы выдать доступ этому сотруднику."
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Добавить этого сотрудника",
                        callback_data=f"approve_staff:{user.id}",
                    )
                ]
            ]
        )
        context.bot.send_message(
            chat_id=admin.telegram_user_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


# ---------------- Базовые команды ----------------


def start(update, context):
    user = update.effective_user
    user_id = user.id

    # Если уже админ — показываем меню
    if is_admin(user_id):
        update.message.reply_text(
            "Привет! Это админ-бот GAIA.\n\n"
            "Используй кнопки внизу:\n"
            "• 📅 Брони на сегодня\n"
            "• 📅 Брони на завтра\n"
            "• 🆕 Новые брони\n"
            "• 📈 Все предстоящие брони\n"
            "• 📆 Выбрать дату",
            reply_markup=get_main_menu(is_superadmin(user_id)),
        )
        return

    # Если не админ — отправляем запрос владельцу
    update.message.reply_text(
        "У вас пока нет доступа к админке GAIA.\n\n"
        "Я отправил владельцу кофейни запрос на подключение. "
        "После одобрения вы сможете пользоваться ботом.",
    )

    notify_superadmins_about_access_request(user, context)


def ping(update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    update.message.reply_text("Pong! Я на связи ✅")


def whoami(update, context):
    """Показать свой Telegram ID и роль."""
    user = update.effective_user
    user_id = user.id
    admin = get_admin(user_id)

    if admin:
        role = "⭐ Суперадмин" if admin.is_superadmin else "Админ"
        active = "активен" if admin.is_active else "деактивирован"
        name = html.escape(admin.full_name or user.full_name or "—")
        username_val = admin.telegram_username or user.username
        username_shown = html.escape(f"@{username_val}") if username_val else "—"

        text = (
            f"Ваш Telegram ID: <code>{user_id}</code>\n"
            f"Имя: {name}\n"
            f"Username: {username_shown}\n"
            f"Роль: {role} ({active})"
        )
    else:
        name = html.escape(user.full_name or "—")
        username_shown = html.escape(f"@{user.username}") if user.username else "—"

        text = (
            f"Ваш Telegram ID: <code>{user_id}</code>\n"
            f"Имя: {name}\n"
            f"Username: {username_shown}\n\n"
            "Вы сейчас не добавлены как администратор в системе GAIA."
        )

    update.message.reply_text(text, parse_mode=ParseMode.HTML)



def staff_list(update, context):
    """Список активных админов (виден всем админам).

    Для суперадмина добавляем inline-кнопки '❌ Удалить' по каждому сотруднику.
    """
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("У вас нет доступа к этому боту.")
        return

    admins = TelegramAdmin.objects.filter(is_active=True).order_by(
        "-is_superadmin", "full_name", "telegram_user_id"
    )

    if not admins.exists():
        update.message.reply_text("Администраторов пока нет.")
        return

    lines = []
    for admin in admins:
        mark = "⭐" if admin.is_superadmin else "•"
        name = html.escape(admin.full_name or "Без имени")
        if admin.telegram_username:
            username_part = f" (@{html.escape(admin.telegram_username)})"
        else:
            username_part = ""
        lines.append(
            f"{mark} {name}{username_part} (ID: <code>{admin.telegram_user_id}</code>)"
        )

    text = "Текущие администраторы:\n" + "\n".join(lines)

    if is_superadmin(user_id):
        buttons_rows: list[list[InlineKeyboardButton]] = []
        for admin in admins:
            if admin.is_superadmin:
                continue
            name = html.escape(admin.full_name or "Без имени")
            if admin.telegram_username:
                username_part = f" (@{html.escape(admin.telegram_username)})"
            else:
                username_part = ""
            btn_text = f"❌ {name}{username_part}"
            buttons_rows.append(
                [
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"remove_staff_inline:{admin.telegram_user_id}",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(buttons_rows) if buttons_rows else None
        update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    else:
        update.message.reply_text(text, parse_mode=ParseMode.HTML)




def add_staff(update, context):
    """Добавить/активировать сотрудника по Telegram ID (только суперадмин)."""
    user_id = update.effective_user.id
    if not is_superadmin(user_id):
        update.message.reply_text("Эта команда доступна только владельцу кофейни.")
        return

    if not context.args:
        update.message.reply_text("Использование: /add_staff <telegram_id>")
        return

    try:
        staff_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("ID должен быть числом.")
        return

    if staff_id == user_id:
        update.message.reply_text("Вы уже являетесь администратором.")
        return

    admin, created = TelegramAdmin.objects.get_or_create(
        telegram_user_id=staff_id,
        defaults={
            "full_name": "",
            "telegram_username": "",
            "is_superadmin": False,
            "is_active": True,
        },
    )

    if not created:
        admin.is_active = True
        admin.save(update_fields=["is_active"])

    update.message.reply_text(
        f"Сотрудник с ID {staff_id} добавлен как администратор и теперь может пользоваться ботом."
    )


def remove_staff(update, context):
    """Деактивировать сотрудника по Telegram ID (только суперадмин, старый способ)."""
    user_id = update.effective_user.id
    if not is_superadmin(user_id):
        update.message.reply_text("Эта команда доступна только владельцу кофейни.")
        return

    if not context.args:
        update.message.reply_text("Использование: /remove_staff <telegram_id>")
        return

    try:
        staff_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("ID должен быть числом.")
        return

    if staff_id == user_id:
        update.message.reply_text("Нельзя удалить самого себя как суперадмина.")
        return

    try:
        admin = TelegramAdmin.objects.get(telegram_user_id=staff_id)
    except TelegramAdmin.DoesNotExist:
        update.message.reply_text(f"Администратор с ID {staff_id} не найден.")
        return

    if admin.is_superadmin:
        update.message.reply_text("Нельзя удалить другого суперадмина.")
        return

    admin.is_active = False
    admin.save(update_fields=["is_active"])

    update.message.reply_text(f"Сотрудник с ID {staff_id} больше не имеет доступа к боту.")


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
    user_id = update.effective_user.id
    menu = get_main_menu(is_superadmin(user_id))

    bookings = Booking.objects.filter(start_time__date=target_date).order_by("start_time")

    if not bookings:
        update.message.reply_text(
            f"На {label} броней нет.",
            reply_markup=menu,
        )
        return

    update.message.reply_text(
        f"Брони на {label}:",
        reply_markup=menu,
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
    user_id = update.effective_user.id
    menu = get_main_menu(is_superadmin(user_id))

    today = date_class.today()
    bookings = (
        Booking.objects
        .filter(start_time__date__gte=today, status="new")
        .order_by("start_time")
    )

    if not bookings:
        update.message.reply_text(
            "Новых предстоящих броней нет.",
            reply_markup=menu,
        )
        return

    update.message.reply_text(
        "🆕 Новые предстоящие брони:",
        reply_markup=menu,
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
    user_id = update.effective_user.id
    menu = get_main_menu(is_superadmin(user_id))

    today = date_class.today()
    bookings = (
        Booking.objects
        .filter(start_time__date__gte=today, status__in=["new", "confirmed"])
        .order_by("start_time")
    )

    if not bookings:
        update.message.reply_text(
            "Предстоящих броней нет.",
            reply_markup=menu,
        )
        return

    update.message.reply_text(
        "📈 Все предстоящие брони:",
        reply_markup=menu,
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
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
                reply_markup=get_main_menu(is_superadmin(user_id)),
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
            reply_markup=get_main_menu(is_superadmin(user_id)),
        )

    else:
        update.message.reply_text(
            "Не понимаю этот ввод. Используй кнопки меню снизу 🙂",
            reply_markup=get_main_menu(is_superadmin(user_id)),
        )


# ---------------- Обработчик нажатий на inline-кнопки по броням ----------------


def booking_callback(update, context):
    """Обрабатываем нажатия на кнопки ℹ️ / ↩ / ✅ / ❌."""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
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


# ---------------- Обработка inline-кнопок approve_staff / remove_staff_inline ----------------


def staff_approval_callback(update, context):
    """Обработка кнопки 'Добавить этого сотрудника' от суперадмина."""
    query = update.callback_query
    approver_id = query.from_user.id

    if not is_superadmin(approver_id):
        query.answer("Только владелец может одобрять доступ.")
        return

    data = query.data  # ожидаем 'approve_staff:<telegram_id>'
    if not data.startswith("approve_staff:"):
        query.answer("Некорректные данные.")
        return

    try:
        staff_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        query.answer("Некорректный ID.")
        return

    admin, created = TelegramAdmin.objects.get_or_create(
        telegram_user_id=staff_id,
        defaults={
            "full_name": "",
            "telegram_username": "",
            "is_superadmin": False,
            "is_active": True,
        },
    )

    if not created:
        admin.is_active = True
        admin.save(update_fields=["is_active"])

    # Обновляем сообщение владельцу
    try:
        query.edit_message_text(
            f"Сотруднику с ID {staff_id} выдан доступ к боту ✅"
        )
    except BadRequest:
        pass

    query.answer("Доступ выдан.")

    # Пытаемся уведомить самого сотрудника
    try:
        context.bot.send_message(
            chat_id=staff_id,
            text="Вам выдали доступ к админ-боту GAIA. "
                 "Нажмите /start, чтобы открыть меню.",
        )
    except Exception:
        pass


def staff_inline_remove_callback(update, context):
    """Удаление сотрудника по inline-кнопке в /staff_list (только суперадмин)."""
    query = update.callback_query
    approver_id = query.from_user.id

    if not is_superadmin(approver_id):
        query.answer("Только владелец может управлять доступом.")
        return

    data = query.data  # ожидаем 'remove_staff_inline:<telegram_id>'
    if not data.startswith("remove_staff_inline:"):
        query.answer("Некорректные данные.")
        return

    try:
        staff_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        query.answer("Некорректный ID.")
        return

    if staff_id == approver_id:
        query.answer("Нельзя удалить самого себя как суперадмина.")
        return

    try:
        admin = TelegramAdmin.objects.get(telegram_user_id=staff_id)
    except TelegramAdmin.DoesNotExist:
        query.answer("Администратор не найден.")
        return

    if admin.is_superadmin:
        query.answer("Нельзя удалить другого суперадмина.")
        return

    admin.is_active = False
    admin.save(update_fields=["is_active"])

    query.answer("Сотрудник удалён.")
    # Сообщение с кнопками оставляем, админ может обновить список командой /staff_list.


# ---------------- main ----------------


def main():
    token = settings.TELEGRAM_BOT_TOKEN
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # Команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ping", ping))
    dp.add_handler(CommandHandler("whoami", whoami))
    dp.add_handler(CommandHandler("staff_list", staff_list))
    dp.add_handler(CommandHandler("add_staff", add_staff))
    dp.add_handler(CommandHandler("remove_staff", remove_staff))

    # Все текстовые сообщения (не команды) — работа с меню и вводом даты
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_menu))

    # Inline approve_staff:<id>
    dp.add_handler(CallbackQueryHandler(staff_approval_callback, pattern=r"^approve_staff:"))

    # Inline remove_staff_inline:<id>
    dp.add_handler(CallbackQueryHandler(staff_inline_remove_callback, pattern=r"^remove_staff_inline:"))

    # Затем обработчик всех остальных inline-кнопок по бронированиям
    dp.add_handler(CallbackQueryHandler(booking_callback))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
