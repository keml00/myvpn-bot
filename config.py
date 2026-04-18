import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Реквизиты
SBER_CARD = os.getenv("SBER_CARD", "2200 7007 XXXX XXXX")
YOOMONEY = os.getenv("YOOMONEY", "410011XXXXXXXXX")
CRYPTO_ADDRESS = os.getenv("CRYPTO_ADDRESS", "your_crypto_address")

# Сервер
SERVER_HOST = os.getenv("SERVER_HOST", "your.server.com")
SERVER_PORT = os.getenv("SERVER_PORT", "443")

# Тарифы
TARIFFS = {
    "1": {
        "name": "1 месяц",
        "price": 200,
        "traffic_gb": 100,
        "emoji": "1️⃣",
        "badge": ""
    },
    "2": {
        "name": "3 месяца",
        "price": 550,
        "traffic_gb": 300,
        "emoji": "2️⃣",
        "badge": "🔥 ПОПУЛЯРНЫЙ"
    },
    "3": {
        "name": "6 месяцев",
        "price": 1000,
        "traffic_gb": 600,
        "emoji": "3️⃣",
        "badge": "💎 ВЫГОДНО"
    },
    "4": {
        "name": "12 месяцев",
        "price": 1800,
        "traffic_gb": 1200,
        "emoji": "4️⃣",
        "badge": "⭐ ЛУЧШИЙ ВЫБОР"
    }
}

# Тексты
WELCOME_TEXT = """Привет! 👋

Сдаю в аренду личные серверы для безопасного интернета.

Что получаешь:
🔥 Свой выделенный сервер (не общий, только твой)
🔥 Полная приватность (никаких логов, никакой слежки)
🔥 Высокая скорость (стримы в 4K без буферизации)

Работает на любых устройствах: iPhone, Android, Windows, Mac.

Настройка за 2 минуты. Инструкция простая.

Выбери период аренды 👇"""

def get_tariffs_text():
    """Генерация текста с тарифами"""
    text = "💳 ТАРИФЫ\n\n"

    for key, tariff in TARIFFS.items():
        savings = ""
        if key == "2":
            savings = "\n   Экономия 50₽"
        elif key == "3":
            savings = "\n   Экономия 200₽"
        elif key == "4":
            savings = "\n   Экономия 600₽"

        badge = f" {tariff['badge']}" if tariff['badge'] else ""

        text += f"{tariff['emoji']} {tariff['name']}{badge}\n"
        text += f"   {tariff['price']}₽ • {tariff['traffic_gb']} ГБ{savings}\n\n"

    text += """---

Трафика хватит на:
• Стримы в HD/4K
• Соцсети без ограничений
• Торренты
• Всё, что угодно

Просто напиши номер тарифа (1, 2, 3 или 4)"""

    return text

def get_payment_text(tariff_key: str):
    """Генерация текста для оплаты"""
    tariff = TARIFFS[tariff_key]

    badge_text = ""
    if tariff_key == "2":
        badge_text = "🔥 Самый популярный тариф.\n\n"
    elif tariff_key == "3":
        badge_text = "💎 Выгодный выбор!\n\n"
    elif tariff_key == "4":
        badge_text = "⭐ Топ! Год без проблем с доступом.\n\n"

    savings = ""
    if tariff_key == "2":
        savings = " → экономишь 50₽"
    elif tariff_key == "3":
        savings = " → экономишь 200₽"
    elif tariff_key == "4":
        savings = " → экономишь 600₽"

    text = f"""{"Отлично!" if tariff_key == "1" else badge_text}
{tariff['price']}₽ за {tariff['name']}{savings}

Оплата:
💳 Карта: {SBER_CARD}
💰 ЮMoney: {YOOMONEY}
🪙 Крипта: {CRYPTO_ADDRESS}

После оплаты скинь скрин сюда — {"сразу" if tariff_key == "1" else "моментально"} выдам доступ.

Обычно это занимает 2-3 минуты."""

    return text

ACCESS_TEXT = """Оплата прошла! ✅

Твой доступ к серверу:

📱 Ссылка для подключения:
`{vpn_key}`

---

КАК ПОДКЛЮЧИТЬСЯ:

iPhone/Android:
1. Скачай приложение V2Box (бесплатно)
2. Открой ссылку выше
3. Нажми "Подключить"
4. Готово

Windows/Mac:
1. Скачай V2RayN
2. Импортируй ссылку
3. Включи
4. Работает

---

Проблемы с подключением? Пиши — помогу.

Низкая скорость? Тоже пиши — поменяем сервер.

Приятного использования! 🚀"""
