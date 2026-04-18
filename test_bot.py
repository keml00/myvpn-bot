"""
Тестовый запуск бота для проверки
"""
import asyncio
import sys

async def test_bot():
    print("=" * 50)
    print("ТЕСТ БОТА")
    print("=" * 50)

    # Проверка конфига
    print("\n1. Проверка конфига...")
    try:
        from config import BOT_TOKEN, ADMIN_ID, TARIFFS
        print(f"   BOT_TOKEN: {BOT_TOKEN[:20]}...")
        print(f"   ADMIN_ID: {ADMIN_ID}")
        print(f"   Тарифов: {len(TARIFFS)}")
        print("   OK")
    except Exception as e:
        print(f"   ОШИБКА: {e}")
        return False

    # Проверка базы данных
    print("\n2. Проверка базы данных...")
    try:
        from database import Database
        db = Database()
        await db.init_db()
        stats = await db.get_stats()
        print(f"   Пользователей: {stats['total_users']}")
        print(f"   Подписок: {stats['active_subs']}")
        print("   OK")
    except Exception as e:
        print(f"   ОШИБКА: {e}")
        return False

    # Проверка импорта бота
    print("\n3. Проверка модулей бота...")
    try:
        from bot import bot, dp, router
        print(f"   Bot ID: {bot.id if hasattr(bot, 'id') else 'не запущен'}")
        print("   OK")
    except Exception as e:
        print(f"   ОШИБКА: {e}")
        return False

    print("\n" + "=" * 50)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 50)
    print("\nДля запуска бота используй:")
    print("  python bot.py")
    print("\nИли запусти прямо сейчас? (y/n): ", end="")

    return True

if __name__ == "__main__":
    result = asyncio.run(test_bot())
    if not result:
        sys.exit(1)
