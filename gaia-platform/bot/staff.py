import html

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
)

from notifications.models import TelegramAdmin
from .auth import get_admin, is_admin, is_superadmin


# ---------- Заявка на доступ для суперадминов ----------


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


# ---------- Команда /whoami ----------


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


# ---------- Команда /staff_list ----------


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


# ---------- /add_staff и /remove_staff (старый способ по ID) ----------


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


# ---------- Inline approve_staff / remove_staff_inline ----------


def staff_approval_callback(update, context):
    """Обработка кнопки 'Добавить этого сотрудника' от суперадмина."""
    from telegram.error import BadRequest  # локальный импорт, чтобы не тянуть наверх

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

    try:
        query.edit_message_text(
            f"Сотруднику с ID {staff_id} выдан доступ к боту ✅"
        )
    except BadRequest:
        pass

    query.answer("Доступ выдан.")

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
