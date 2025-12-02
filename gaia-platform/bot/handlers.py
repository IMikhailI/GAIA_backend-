from telegram import ParseMode

from .auth import is_admin, is_superadmin
from .bookings import get_main_menu
from .staff import notify_superadmins_about_access_request


def start(update, context):
    user = update.effective_user
    user_id = user.id

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
