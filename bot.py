import asyncio
import logging
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import Database
from config import *
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
db = Database()

# Состояния
class UserStates(StatesGroup):
    waiting_tariff = State()
    waiting_payment = State()

# ============= ПОЛЬЗОВАТЕЛЬСКИЕ ХЕНДЛЕРЫ =============

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await db.update_last_active(message.from_user.id)

    # Проверяем активную подписку
    subscription = await db.get_user_subscription(message.from_user.id)
    if subscription:
        await message.answer(
            f"У тебя уже есть активная подписка!\n\n"
            f"Тариф: {subscription['tariff']}\n"
            f"Действует до: {subscription['end_date'][:10]}\n\n"
            f"Твой ключ:\n`{subscription['vpn_key']}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Приветствие
    await message.answer(WELCOME_TEXT)

    # Тарифы с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{tariff['emoji']} {tariff['name']} — {tariff['price']}₽ ({tariff['traffic_gb']} ГБ) {tariff['badge']}",
            callback_data=f"tariff_{key}"
        )]
        for key, tariff in TARIFFS.items()
    ])

    await message.answer(
        "💳 ВЫБЕРИ ПЕРИОД АРЕНДЫ:\n\n"
        "Что входит в трафик:\n"
        "• Стримы в HD/4K\n"
        "• Соцсети без ограничений\n"
        "• Торренты и загрузки\n"
        "• Любое использование",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_button(callback: CallbackQuery):
    """Обработка выбора тарифа через кнопку"""
    tariff_key = callback.data.split("_")[1]

    if tariff_key not in TARIFFS:
        await callback.answer("Ошибка выбора тарифа", show_alert=True)
        return

    tariff = TARIFFS[tariff_key]

    # Кнопка для перехода в личку
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать @keml00", url="https://t.me/keml00")]
    ])

    await callback.message.edit_text(
        f"Отлично! Ты выбрал:\n\n"
        f"{tariff['emoji']} Аренда на {tariff['name']}\n"
        f"💰 Цена: {tariff['price']}₽\n"
        f"📊 Трафик: {tariff['traffic_gb']} ГБ\n"
        f"⏱ Период: {tariff['name']}\n\n"
        f"Напиши @keml00 и скопируй это сообщение:\n\n"
        f"<code>Хочу арендовать сервер\n\n"
        f"Период: {tariff['name']}\n"
        f"Цена: {tariff['price']}₽\n"
        f"Трафик: {tariff['traffic_gb']} ГБ</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    await callback.answer()

@router.message(StateFilter(UserStates.waiting_tariff))
async def process_tariff_selection(message: Message):
    """Выбор тарифа (старый метод через текст - оставляем для совместимости)"""
    await message.answer("Используй кнопки выше для выбора тарифа 👆")

@router.message(StateFilter(UserStates.waiting_payment), F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext):
    """Получение скриншота оплаты"""
    data = await state.get_data()
    tariff_key = data.get("tariff")

    if not tariff_key:
        await message.answer("Ошибка. Начни заново: /start")
        await state.clear()
        return

    tariff = TARIFFS[tariff_key]
    photo_id = message.photo[-1].file_id

    # Создаём платёж в БД
    payment_id = await db.create_payment(
        user_id=message.from_user.id,
        tariff=tariff["name"],
        amount=tariff["price"],
        payment_method="screenshot",
        screenshot_file_id=photo_id
    )

    # Уведомляем пользователя
    await message.answer(
        "Скриншот получен! ✅\n\n"
        "Проверяю оплату... Обычно это занимает 2-3 минуты.\n"
        "Как только подтвержу — сразу пришлю доступ."
    )

    # Уведомляем админа
    await notify_admin_new_payment(payment_id, message.from_user, tariff, photo_id)

    await state.clear()

@router.message(StateFilter(UserStates.waiting_payment))
async def process_payment_no_photo(message: Message):
    """Если прислали не фото"""
    await message.answer("Пришли скриншот оплаты (фото) 📸")

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Проверка статуса подписки"""
    subscription = await db.get_user_subscription(message.from_user.id)

    if not subscription:
        await message.answer("У тебя нет активной подписки.\n\nЧтобы купить: /start")
        return

    await message.answer(
        f"Твоя подписка:\n\n"
        f"Тариф: {subscription['tariff']}\n"
        f"Трафик: {subscription['traffic_gb']} ГБ\n"
        f"Действует до: {subscription['end_date'][:10]}\n\n"
        f"Твой ключ:\n`{subscription['vpn_key']}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ============= АДМИН ХЕНДЛЕРЫ =============

async def notify_admin_new_payment(payment_id: int, user, tariff: dict, photo_id: str):
    """Уведомление админа о новом платеже"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{payment_id}")
        ]
    ])

    text = (
        f"💰 НОВЫЙ ПЛАТЁЖ #{payment_id}\n\n"
        f"От: {user.first_name} (@{user.username or 'нет'})\n"
        f"ID: {user.id}\n"
        f"Тариф: {tariff['name']}\n"
        f"Сумма: {tariff['price']}₽"
    )

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=text,
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_payment(callback: CallbackQuery):
    """Подтверждение платежа админом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Только для админа", show_alert=True)
        return

    payment_id = int(callback.data.split("_")[1])

    # Генерируем VPN ключ
    vpn_key = generate_vpn_key()

    # Подтверждаем платёж
    result = await db.confirm_payment(payment_id, vpn_key)

    if not result:
        await callback.answer("Ошибка: платёж не найден", show_alert=True)
        return

    # Отправляем доступ пользователю
    await bot.send_message(
        chat_id=result["user_id"],
        text=ACCESS_TEXT.format(vpn_key=vpn_key),
        parse_mode=ParseMode.MARKDOWN
    )

    # Уведомляем админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ ПОДТВЕРЖДЁН"
    )
    await callback.answer("Платёж подтверждён, доступ выдан")

@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    """Отклонение платежа админом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Только для админа", show_alert=True)
        return

    payment_id = int(callback.data.split("_")[1])

    # Отклоняем платёж
    await db.reject_payment(payment_id)

    # Уведомляем админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ ОТКЛОНЁН"
    )
    await callback.answer("Платёж отклонён")

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if message.from_user.id != ADMIN_ID:
        return

    stats = await db.get_stats()

    text = (
        "📊 СТАТИСТИКА\n\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Активных подписок: {stats['active_subs']}\n"
        f"Ожидают проверки: {stats['pending_payments']}\n\n"
        f"💰 Доход за сегодня: {stats['today_revenue']}₽\n"
        f"💰 Доход за всё время: {stats['total_revenue']}₽\n\n"
        "Команды:\n"
        "/pending - ожидающие платежи\n"
        "/broadcast - рассылка"
    )

    await message.answer(text)

@router.message(Command("pending"))
async def cmd_pending(message: Message):
    """Список ожидающих платежей"""
    if message.from_user.id != ADMIN_ID:
        return

    payments = await db.get_pending_payments()

    if not payments:
        await message.answer("Нет ожидающих платежей")
        return

    for payment in payments:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{payment['id']}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{payment['id']}")
            ]
        ])

        text = (
            f"💰 ПЛАТЁЖ #{payment['id']}\n\n"
            f"От: {payment['first_name']} (@{payment['username'] or 'нет'})\n"
            f"ID: {payment['user_id']}\n"
            f"Тариф: {payment['tariff']}\n"
            f"Сумма: {payment['amount']}₽\n"
            f"Дата: {payment['created_at'][:16]}"
        )

        if payment['screenshot_file_id']:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=payment['screenshot_file_id'],
                caption=text,
                reply_markup=keyboard
            )
        else:
            await message.answer(text, reply_markup=keyboard)

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def generate_vpn_key() -> str:
    """Генерация ключа доступа к серверу (заглушка)"""
    # TODO: Интегрировать с реальным сервером
    key_id = str(uuid.uuid4())
    return f"vless://{key_id}@{SERVER_HOST}:{SERVER_PORT}?encryption=none&security=tls&type=tcp"

# ============= ЗАПУСК БОТА =============

async def main():
    """Запуск бота"""
    # Проверка конфигурации
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("BOT_TOKEN не установлен! Проверь переменные окружения.")
        sys.exit(1)

    if not ADMIN_ID or ADMIN_ID == 0:
        logger.error("ADMIN_ID не установлен! Проверь переменные окружения.")
        sys.exit(1)

    logger.info(f"Запуск бота с токеном: {BOT_TOKEN[:20]}...")
    logger.info(f"Admin ID: {ADMIN_ID}")

    # Инициализация БД
    await db.init_db()
    logger.info("База данных инициализирована")

    # Регистрация роутера
    dp.include_router(router)

    # Уведомление админа о запуске
    try:
        await bot.send_message(ADMIN_ID, "🤖 Бот запущен!")
        logger.info("Уведомление админу отправлено")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админу: {e}")

    # Запуск polling
    logger.info("Бот запущен и работает...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
