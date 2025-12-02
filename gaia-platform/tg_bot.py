import os
import django

from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

# --- Настройка Django окружения ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gaia.settings")
django.setup()

from django.conf import settings

from bot.handlers import start, ping
from bot.bookings import handle_menu, booking_callback
from bot.staff import (
    whoami,
    staff_list,
    add_staff,
    remove_staff,
    staff_approval_callback,
    staff_inline_remove_callback,
)
from bot.menu_files import (
    handle_menu_document,
    menu_list,
    menu_file_remove_callback,
)

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
    dp.add_handler(CommandHandler("menu_list", menu_list))

    # Все текстовые сообщения (не команды) — работа с меню и вводом даты
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_menu))

    # Inline approve_staff:<id>
    dp.add_handler(CallbackQueryHandler(staff_approval_callback, pattern=r"^approve_staff:"))

    # Inline remove_staff_inline:<id>
    dp.add_handler(CallbackQueryHandler(staff_inline_remove_callback, pattern=r"^remove_staff_inline:"))

    # Документы — загрузка PDF меню
    dp.add_handler(MessageHandler(Filters.document, handle_menu_document))

    dp.add_handler(CallbackQueryHandler(staff_approval_callback, pattern=r"^approve_staff:"))
    dp.add_handler(CallbackQueryHandler(staff_inline_remove_callback, pattern=r"^remove_staff_inline:"))
    dp.add_handler(CallbackQueryHandler(menu_file_remove_callback, pattern=r"^remove_menu_file:"))
    
    # Затем обработчик всех остальных inline-кнопок по бронированиям
    dp.add_handler(CallbackQueryHandler(booking_callback))



    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
