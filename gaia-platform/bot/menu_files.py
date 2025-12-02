from io import BytesIO

from django.core.files.base import ContentFile
from django.db.models import Max

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from menus.models import MenuFile
from .auth import is_admin, is_superadmin


def handle_menu_document(update, context):
    """
    Обработка входящих документов.
    Если это PDF и отправитель — админ, сохраняем как MenuFile.
    """
    user = update.effective_user
    user_id = user.id

    if not is_admin(user_id):
        return

    message = update.message
    document = message.document

    if not document:
        return

    mime_type = document.mime_type or ""
    if mime_type != "application/pdf":
        message.reply_text("Принимаю только PDF файлы для меню.")
        return

    tg_file = context.bot.get_file(document.file_id)
    bio = BytesIO()
    tg_file.download(out=bio)
    bio.seek(0)

    max_sort = MenuFile.objects.aggregate(m=Max("sort_order"))["m"] or 0
    new_sort = max_sort + 10

    title = document.file_name or "Меню"
    menu_file = MenuFile(title=title, sort_order=new_sort)

    menu_file.file.save(document.file_name or "menu.pdf", ContentFile(bio.read()))
    menu_file.save()

    message.reply_text(
        f"Файл меню сохранён:\n"
        # f"• ID: {menu_file.id}\n"
        f"• Название: {menu_file.title}\n"
        # f"• Порядок: {menu_file.sort_order}"
    )


def menu_list(update, context):
    """
    /menu_list — показать список активных PDF-страниц меню.
    Для суперадмина — добавить кнопки ❌ удалить.
    Плюс отправить сами PDF-файлы в чат.
    """
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("У вас нет доступа к этому боту.")
        return

    menus = MenuFile.objects.filter(is_active=True).order_by("sort_order", "created_at")

    if not menus.exists():
        update.message.reply_text("Меню пока не загружено.")
        return

    # 1) Текстовый список
    lines = []
    for mf in menus:
        lines.append(
            f"• {mf.title} "
        )

    text = "Текущий файл меню:\n" + "\n".join(lines)

    # 2) Кнопки удаления для суперадмина
    reply_markup = None
    if is_superadmin(user_id):
        buttons_rows = []
        for mf in menus:
            btn_text = f"❌ {mf.title[:40]}"
            buttons_rows.append(
                [
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"remove_menu_file:{mf.id}",
                    )
                ]
            )
        reply_markup = InlineKeyboardMarkup(buttons_rows) if buttons_rows else None

    update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )

    # 3) Отправляем сами PDF-файлы меню
    for mf in menus:
        try:
            update.message.reply_document(
                document=mf.file,
                filename=mf.title or None,
                caption=mf.title or None,
            )
        except Exception:
            # Если вдруг какой-то файл битый/недоступен — не валим команду целиком
            continue


def menu_file_remove_callback(update, context):
    """
    Обработка inline-кнопок remove_menu_file:<id>
    """
    query = update.callback_query
    user_id = query.from_user.id

    if not is_superadmin(user_id):
        query.answer("Удалять меню может только владелец.")
        return

    data = query.data  # ожидаем 'remove_menu_file:<id>'
    if not data.startswith("remove_menu_file:"):
        query.answer("Некорректные данные.")
        return

    try:
        menu_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        query.answer("Некорректный ID.")
        return

    try:
        mf = MenuFile.objects.get(id=menu_id)
    except MenuFile.DoesNotExist:
        query.answer("Файл меню не найден.")
        return

    mf.is_active = False
    mf.save(update_fields=["is_active"])

    query.answer("Файл меню скрыт (не будет виден на сайте).")
