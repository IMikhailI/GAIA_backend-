from datetime import datetime, time

from django.utils import timezone

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from halls.models import Hall, BlockedSlot
from .auth import is_admin

# Состояния разговора
(
    CHOOSING_HALL,
    ENTERING_DATE,
    ENTERING_TIME_RANGE,
    ENTERING_REASON,
) = range(4)


def _local_tz():
    # Берём таймзону Django (Europe/Moscow в твоих настройках)
    return timezone.get_current_timezone()


def start_block_time(update: Update, context: CallbackContext):
    """Старт команды /block_time — просим выбрать зал."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("У вас нет прав для блокировки времени.")
        return ConversationHandler.END

    halls = Hall.objects.all().order_by("id")
    if not halls.exists():
        update.message.reply_text("Пока не создано ни одного зала.")
        return ConversationHandler.END

    buttons = []
    for hall in halls:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{hall.id}. {hall.name}",
                    callback_data=f"block_hall:{hall.id}",
                )
            ]
        )

    update.message.reply_text(
        "Выберите зал для блокировки времени:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CHOOSING_HALL


def hall_chosen(update: Update, context: CallbackContext):
    """Обработка выбора зала из inline-кнопок."""
    query = update.callback_query
    query.answer()

    data = query.data  # вида "block_hall:<id>"
    _, hall_id_str = data.split(":")
    hall_id = int(hall_id_str)

    try:
        hall = Hall.objects.get(id=hall_id)
    except Hall.DoesNotExist:
        query.edit_message_text("Зал не найден.")
        return ConversationHandler.END

    context.user_data["block_hall_id"] = hall.id

    query.edit_message_text(
        f"Зал: {hall.name}\n\n"
        "Теперь введите дату для блокировки в формате ДД.ММ.ГГГГ\n"
        "Например: 10.12.2025"
    )
    return ENTERING_DATE


def date_entered(update: Update, context: CallbackContext):
    """Принимаем дату от пользователя."""
    text = (update.message.text or "").strip()
    try:
        day, month, year = map(int, text.split("."))
        dt = datetime(year, month, day)
    except Exception:
        update.message.reply_text(
            "Не смог разобрать дату.\n"
            "Введите в формате ДД.ММ.ГГГГ, например: 10.12.2025"
        )
        return ENTERING_DATE

    context.user_data["block_date"] = dt.date()

    update.message.reply_text(
        "Теперь введите интервал времени в формате ЧЧ:ММ-ЧЧ:ММ\n"
        "Например: 14:00-18:00"
    )
    return ENTERING_TIME_RANGE


def time_range_entered(update: Update, context: CallbackContext):
    """Принимаем диапазон времени."""
    text = (update.message.text or "").strip()
    try:
        start_str, end_str = text.split("-")
        start_str = start_str.strip()
        end_str = end_str.strip()

        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))

        start_t = time(sh, sm)
        end_t = time(eh, em)

        if end_t <= start_t:
            raise ValueError("end <= start")
    except Exception:
        update.message.reply_text(
            "Не смог разобрать время.\n"
            "Введите в формате ЧЧ:ММ-ЧЧ:ММ, например: 14:00-18:00"
        )
        return ENTERING_TIME_RANGE

    date = context.user_data.get("block_date")
    hall_id = context.user_data.get("block_hall_id")
    if not date or not hall_id:
        update.message.reply_text("Что-то пошло не так, попробуйте ещё раз.")
        return ConversationHandler.END

    # Собираем наивные datetime (без таймзоны)
    naive_start = datetime.combine(date, start_t)
    naive_end = datetime.combine(date, end_t)

    # Делаем их "осознанными" в текущей (московской) таймзоне Django
    tz = _local_tz()
    start_dt = timezone.make_aware(naive_start, tz)
    end_dt = timezone.make_aware(naive_end, tz)

    context.user_data["block_start_dt"] = start_dt
    context.user_data["block_end_dt"] = end_dt

    update.message.reply_text(
        "Если хотите, укажите причину блокировки (или отправьте '-' чтобы пропустить):"
    )
    return ENTERING_REASON


def reason_entered(update: Update, context: CallbackContext):
    """Принимаем причину и создаём BlockedSlot."""
    reason_text = (update.message.text or "").strip()
    if reason_text == "-":
        reason_text = ""

    hall_id = context.user_data.get("block_hall_id")
    start_dt = context.user_data.get("block_start_dt")
    end_dt = context.user_data.get("block_end_dt")

    if not (hall_id and start_dt and end_dt):
        update.message.reply_text("Не удалось собрать данные для блокировки.")
        return ConversationHandler.END

    try:
        hall = Hall.objects.get(id=hall_id)
    except Hall.DoesNotExist:
        update.message.reply_text("Зал не найден.")
        return ConversationHandler.END

    # TODO: при желании здесь можно проверить пересечения с бронями и предупредить

    BlockedSlot.objects.create(
        hall=hall,
        start_time=start_dt,
        end_time=end_dt,
        reason=reason_text,
    )

    update.message.reply_text(
        f"Время заблокировано:\n"
        f"Зал: {hall.name}\n"
        f"Дата: {start_dt.date().strftime('%d.%m.%Y')}\n"
        f"Время: {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}\n"
        + (f"Причина: {reason_text}" if reason_text else "")
    )

    # чистим user_data
    context.user_data.pop("block_hall_id", None)
    context.user_data.pop("block_date", None)
    context.user_data.pop("block_start_dt", None)
    context.user_data.pop("block_end_dt", None)

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Отмена блокировки.")
    context.user_data.clear()
    return ConversationHandler.END


def build_block_time_conversation():
    """Возвращает ConversationHandler для регистрации в tg_bot.py"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("block_time", start_block_time),
        ],
        states={
            CHOOSING_HALL: [
                # выбор зала по кнопкам
                CallbackQueryHandler(hall_chosen, pattern=r"^block_hall:"),
                # если юзер опять ввёл /block_time — просто перезапускаем
                CommandHandler("block_time", start_block_time),
                # и даём возможность отменить
                CommandHandler("cancel", cancel),
            ],
            ENTERING_DATE: [
                MessageHandler(Filters.text & ~Filters.command, date_entered),
                CommandHandler("block_time", start_block_time),
                CommandHandler("cancel", cancel),
            ],
            ENTERING_TIME_RANGE: [
                MessageHandler(Filters.text & ~Filters.command, time_range_entered),
                CommandHandler("block_time", start_block_time),
                CommandHandler("cancel", cancel),
            ],
            ENTERING_REASON: [
                MessageHandler(Filters.text & ~Filters.command, reason_entered),
                CommandHandler("block_time", start_block_time),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,   # <- ВАЖНО: разрешаем повторный вход по /block_time
        name="block_time_conversation",
        persistent=False,
    )

def list_blocked_slots(update: Update, context: CallbackContext):
    """
    /blocked_slots — показать список активных блокировок
    с кнопками для их отмены.
    """
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("У вас нет прав для просмотра блокировок.")
        return

    now = timezone.now()
    slots = BlockedSlot.objects.filter(end_time__gte=now).order_by("start_time")

    if not slots.exists():
        update.message.reply_text("Активных блокировок сейчас нет.")
        return

    lines = []
    buttons = []

    for slot in slots:
        start = timezone.localtime(slot.start_time)
        end = timezone.localtime(slot.end_time)

        line = (
            f"ID {slot.id}: {slot.hall.name} — "
            f"{start.strftime('%d.%m.%Y %H:%M')}–{end.strftime('%H:%M')}"
        )
        if slot.reason:
            line += f" ({slot.reason})"
        lines.append(line)

        btn_text = f"❌ {slot.hall.name} {start.strftime('%d.%m %H:%M')}"
        buttons.append(
            [
                InlineKeyboardButton(
                    btn_text,
                    callback_data=f"unblock_slot:{slot.id}",
                )
            ]
        )

    text = "Активные блокировки:\n\n" + "\n".join(lines)

    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def unblock_slot_callback(update: Update, context: CallbackContext):
    """
    Обработка нажатия на кнопку 'unblock_slot:<id>' — снятие блокировки.
    """
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        query.answer("У вас нет прав для снятия блокировок.")
        return

    data = query.data  # ожидаем 'unblock_slot:<id>'
    try:
        _, slot_id_str = data.split(":")
        slot_id = int(slot_id_str)
    except Exception:
        query.answer("Некорректные данные.")
        return

    try:
        slot = BlockedSlot.objects.get(id=slot_id)
    except BlockedSlot.DoesNotExist:
        query.answer("Блокировка уже удалена.")
        # Можно ещё отредактировать сообщение, но не обязательно
        return

    slot.delete()
    query.answer("Блокировка снята.")
    # По желанию можно обновить текст сообщения:
    query.edit_message_text("Блокировка снята.")

