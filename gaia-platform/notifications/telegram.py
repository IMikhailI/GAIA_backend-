import requests
from django.conf import settings


def send_telegram_message(chat_id: int, text: str):
    """
    Простая отправка сообщения в Telegram от имени бота.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",  # чтобы <b>...</b> работало
    }

    try:
        requests.post(url, data=payload, timeout=5)
    except requests.RequestException:
        # чтобы сбой Телеги не ломал всё приложение/бота
        pass
