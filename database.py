import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_path: str = "vpn_bot.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица подписок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tariff TEXT,
                    price INTEGER,
                    traffic_gb INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    vpn_key TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица платежей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tariff TEXT,
                    amount INTEGER,
                    payment_method TEXT,
                    screenshot_file_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица статистики
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    new_users INTEGER DEFAULT 0,
                    payments_count INTEGER DEFAULT 0,
                    revenue INTEGER DEFAULT 0
                )
            """)

            await db.commit()

    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Добавить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            """, (user_id, username, first_name))
            await db.commit()

    async def update_last_active(self, user_id: int):
        """Обновить время последней активности"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            await db.commit()

    async def create_payment(self, user_id: int, tariff: str, amount: int,
                           payment_method: str, screenshot_file_id: str = None) -> int:
        """Создать платёж"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO payments (user_id, tariff, amount, payment_method, screenshot_file_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, tariff, amount, payment_method, screenshot_file_id))
            await db.commit()
            return cursor.lastrowid

    async def confirm_payment(self, payment_id: int, vpn_key: str) -> Dict:
        """Подтвердить платёж и создать подписку"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем данные платежа
            async with db.execute("""
                SELECT user_id, tariff, amount FROM payments WHERE id = ?
            """, (payment_id,)) as cursor:
                payment = await cursor.fetchone()

            if not payment:
                return None

            user_id, tariff, amount = payment

            # Определяем параметры подписки
            tariff_params = {
                "1 месяц": (1, 100),
                "3 месяца": (3, 300),
                "6 месяцев": (6, 600),
                "12 месяцев": (12, 1200)
            }

            months, traffic_gb = tariff_params.get(tariff, (1, 100))

            start_date = datetime.now()
            end_date = start_date + timedelta(days=30 * months)

            # Создаём подписку
            await db.execute("""
                INSERT INTO subscriptions
                (user_id, tariff, price, traffic_gb, start_date, end_date, vpn_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, tariff, amount, traffic_gb, start_date, end_date, vpn_key))

            # Обновляем статус платежа
            await db.execute("""
                UPDATE payments
                SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (payment_id,))

            await db.commit()

            return {
                "user_id": user_id,
                "tariff": tariff,
                "end_date": end_date,
                "vpn_key": vpn_key
            }

    async def reject_payment(self, payment_id: int):
        """Отклонить платёж"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE payments SET status = 'rejected' WHERE id = ?
            """, (payment_id,))
            await db.commit()

    async def get_pending_payments(self) -> List[Dict]:
        """Получить ожидающие платежи"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT p.id, p.user_id, u.username, u.first_name,
                       p.tariff, p.amount, p.payment_method, p.screenshot_file_id, p.created_at
                FROM payments p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "username": row[2],
                        "first_name": row[3],
                        "tariff": row[4],
                        "amount": row[5],
                        "payment_method": row[6],
                        "screenshot_file_id": row[7],
                        "created_at": row[8]
                    }
                    for row in rows
                ]

    async def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Получить активную подписку пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT tariff, end_date, traffic_gb, vpn_key
                FROM subscriptions
                WHERE user_id = ? AND is_active = 1 AND end_date > CURRENT_TIMESTAMP
                ORDER BY end_date DESC
                LIMIT 1
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "tariff": row[0],
                        "end_date": row[1],
                        "traffic_gb": row[2],
                        "vpn_key": row[3]
                    }
                return None

    async def get_stats(self) -> Dict:
        """Получить статистику"""
        async with aiosqlite.connect(self.db_path) as db:
            # Всего пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]

            # Активных подписок
            async with db.execute("""
                SELECT COUNT(*) FROM subscriptions
                WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
            """) as cursor:
                active_subs = (await cursor.fetchone())[0]

            # Ожидающих платежей
            async with db.execute("""
                SELECT COUNT(*) FROM payments WHERE status = 'pending'
            """) as cursor:
                pending_payments = (await cursor.fetchone())[0]

            # Доход за всё время
            async with db.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'confirmed'
            """) as cursor:
                total_revenue = (await cursor.fetchone())[0]

            # Доход за сегодня
            async with db.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payments
                WHERE status = 'confirmed' AND DATE(confirmed_at) = DATE('now')
            """) as cursor:
                today_revenue = (await cursor.fetchone())[0]

            return {
                "total_users": total_users,
                "active_subs": active_subs,
                "pending_payments": pending_payments,
                "total_revenue": total_revenue,
                "today_revenue": today_revenue
            }

    async def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Получить последних активных пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, first_name, last_active
                FROM users
                ORDER BY last_active DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "first_name": row[2],
                        "last_active": row[3]
                    }
                    for row in rows
                ]
