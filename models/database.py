import asyncpg
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
        self.is_connected = False
        self.db_config = self._parse_connection_string(connection_string)

    def _parse_connection_string(self, url: str) -> dict:
        from urllib.parse import urlparse

        if url.startswith('postgresql+asyncpg://'):
            url = url.replace('postgresql+asyncpg://', 'postgresql://')
        elif url.startswith('postgres+asyncpg://'):
            url = url.replace('postgres+asyncpg://', 'postgresql://')

        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'user': parsed.username or 'postgres',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') or 'pulse_traders'
        }

    async def connect(self) -> bool:
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                min_size=5,
                max_size=20
            )
            self.is_connected = True
            await self.create_tables()
            logger.info("✅ PostgreSQL подключено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка PostgreSQL: {e}")
            self.is_connected = False
            return False

    async def close(self):
        try:
            if self.pool:
                await self.pool.close()
                self.is_connected = False
                logger.info("✅ PostgreSQL закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия: {e}")

    async def create_tables(self):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cryptocurrencies (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) UNIQUE NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        display_name VARCHAR(10),
                        emoji VARCHAR(5),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE,
                        username VARCHAR(100),
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        email VARCHAR(255) UNIQUE,
                        password_hash VARCHAR(255),
                        google_id VARCHAR(255) UNIQUE,
                        is_admin BOOLEAN DEFAULT FALSE,
                        is_banned BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        verified_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS subscription_tiers (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        display_name VARCHAR(100) NOT NULL,
                        price DECIMAL(10, 2) NOT NULL,
                        currency VARCHAR(3) DEFAULT 'USD',
                        monthly_predictions INT NOT NULL,
                        daily_predictions INT NOT NULL,
                        features TEXT,
                        description TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        display_order INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_subscriptions (
                        id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL UNIQUE,
                        tier_id INT NOT NULL,
                        status VARCHAR(50) DEFAULT 'active',
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (tier_id) REFERENCES subscription_tiers(id)
                    )
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_limits (
                        id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL UNIQUE,
                        predictions_used_today INT DEFAULT 0,
                        predictions_used_month INT DEFAULT 0,
                        predictions_limit_daily INT DEFAULT 5,
                        predictions_limit_monthly INT DEFAULT 30,
                        is_premium BOOLEAN DEFAULT FALSE,
                        last_reset_daily TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_reset_monthly TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_history (
                        id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        predicted_price DECIMAL(20, 8),
                        confidence DECIMAL(5, 2),
                        signal VARCHAR(50),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_verifications (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        code VARCHAR(6) NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_email_verifications_email ON email_verifications(email)
                """)

                logger.info("✅ Таблицы PostgreSQL созданы")
        except Exception as e:
            logger.error(f"❌ Ошибка таблиц: {e}")

    # ПОЛЬЗОВАТЕЛИ
    async def get_or_create_user(self, telegram_id: int, username: str = "",
                                 first_name: str = "", last_name: str = "") -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)

                if user:
                    return dict(user)

                async with conn.transaction():
                    user = await conn.fetchrow("""
                        INSERT INTO users (telegram_id, username, first_name, last_name, is_active)
                        VALUES ($1, $2, $3, $4, TRUE)
                        RETURNING *
                    """, telegram_id, username, first_name, last_name)

                    await conn.execute("""
                        INSERT INTO prediction_limits (user_id, predictions_limit_daily, predictions_limit_monthly)
                        VALUES ($1, 5, 5)
                    """, user['id'])

                    return dict(user)
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя: {e}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя: {e}")
            return None

    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                users = await conn.fetch("""
                    SELECT u.*, pl.predictions_used_month, pl.predictions_limit_monthly
                    FROM users u
                    LEFT JOIN prediction_limits pl ON u.id = pl.user_id
                    ORDER BY u.created_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
                return [dict(u) for u in users]
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей: {e}")
            return []

    async def get_users_count(self) -> int:
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM users")
                return result or 0
        except Exception as e:
            logger.error(f"❌ Ошибка счета: {e}")
            return 0

    async def update_user_status(self, user_id: int, is_admin: bool = None, is_banned: bool = None) -> bool:
        try:
            async with self.pool.acquire() as conn:
                updates = []
                params = []

                if is_admin is not None:
                    updates.append(f"is_admin = ${len(params) + 1}")
                    params.append(is_admin)
                if is_banned is not None:
                    updates.append(f"is_banned = ${len(params) + 1}")
                    params.append(is_banned)

                if not updates:
                    return False

                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${len(params)}"
                await conn.execute(query, *params)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления: {e}")
            return False

    # КРИПТОВАЛЮТЫ
    async def add_cryptocurrency(self, symbol: str, name: str, display_name: str, emoji: str = "") -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cryptocurrencies (symbol, name, display_name, emoji)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (symbol) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                """, symbol, name, display_name, emoji)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления: {e}")
            return False

    async def get_all_cryptocurrencies(self) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                cryptos = await conn.fetch("""
                    SELECT * FROM cryptocurrencies WHERE is_active = TRUE ORDER BY symbol
                """)
                return [dict(c) for c in cryptos]
        except Exception as e:
            logger.error(f"❌ Ошибка получения крипто: {e}")
            return []

    async def search_cryptocurrencies(self, query: str) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                cryptos = await conn.fetch("""
                    SELECT * FROM cryptocurrencies
                    WHERE symbol ILIKE $1 OR name ILIKE $2
                    ORDER BY symbol LIMIT 20
                """, f"%{query}%", f"%{query}%")
                return [dict(c) for c in cryptos]
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    # ЛИМИТЫ
    async def check_prediction_limit(self, user_id: int) -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE prediction_limits
                    SET predictions_used_today = 0, last_reset_daily = CURRENT_TIMESTAMP
                    WHERE user_id = $1 AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reset_daily)) > 86400
                """, user_id)

                await conn.execute("""
                    UPDATE prediction_limits
                    SET predictions_used_month = 0, last_reset_monthly = CURRENT_TIMESTAMP
                    WHERE user_id = $1 AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reset_monthly)) > 2592000
                """, user_id)

                limit = await conn.fetchrow("SELECT * FROM prediction_limits WHERE user_id = $1", user_id)
                return dict(limit) if limit else None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки лимита: {e}")
            return None

    async def save_prediction(self, user_id: int, symbol: str, predicted_price: float,
                              confidence: float, signal: str) -> bool:
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("""
                        INSERT INTO prediction_history (user_id, symbol, predicted_price, confidence, signal)
                        VALUES ($1, $2, $3, $4, $5)
                    """, user_id, symbol, predicted_price, confidence, signal)

                    await conn.execute("""
                        UPDATE prediction_limits
                        SET predictions_used_today = predictions_used_today + 1,
                            predictions_used_month = predictions_used_month + 1
                        WHERE user_id = $1
                    """, user_id)
                    return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения: {e}")
            return False

    async def get_user_prediction_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                predictions = await conn.fetch("""
                    SELECT * FROM prediction_history
                    WHERE user_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """, user_id, limit)
                return [dict(p) for p in predictions]
        except Exception as e:
            logger.error(f"❌ Ошибка истории: {e}")
            return []

    # ПОДПИСКИ
    async def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                sub = await conn.fetchrow("""
                    SELECT us.*, st.* FROM user_subscriptions us
                    LEFT JOIN subscription_tiers st ON us.tier_id = st.id
                    WHERE us.user_id = $1
                """, user_id)
                return dict(sub) if sub else None
        except Exception as e:
            logger.error(f"❌ Ошибка подписки: {e}")
            return None

    async def get_all_subscription_tiers(self) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                tiers = await conn.fetch("""
                    SELECT * FROM subscription_tiers
                    WHERE is_active = TRUE
                    ORDER BY display_order
                """)
                return [dict(t) for t in tiers]
        except Exception as e:
            logger.error(f"❌ Ошибка тарифов: {e}")
            return []

    async def create_subscription_tier(self, name: str, display_name: str, price: float,
                                       monthly_predictions: int, daily_predictions: int,
                                       features: str = "", description: str = "",
                                       display_order: int = 0) -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                tier = await conn.fetchrow("""
                    INSERT INTO subscription_tiers
                    (name, display_name, price, monthly_predictions, daily_predictions, features, description, display_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING *
                """, name, display_name, price, monthly_predictions, daily_predictions, features, description,
                                           display_order)
                return dict(tier) if tier else None
        except Exception as e:
            logger.error(f"❌ Ошибка создания тарифа: {e}")
            return None

    async def subscribe_user(self, user_id: int, tier_id: int, months: int = 1) -> bool:
        try:
            async with self.pool.acquire() as conn:
                expires_at = datetime.now() + timedelta(days=30 * months)
                await conn.execute("""
                    INSERT INTO user_subscriptions (user_id, tier_id, expires_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE SET tier_id = $2, expires_at = $3
                """, user_id, tier_id, expires_at)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка подписки: {e}")
            return False

    async def get_admin_stats(self) -> Dict:
        try:
            async with self.pool.acquire() as conn:
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

                active_users = await conn.fetchval("""
                    SELECT COUNT(*) FROM users
                    WHERE last_active > CURRENT_TIMESTAMP - INTERVAL '7 days'
                """)

                premium_users = await conn.fetchval("""
                    SELECT COUNT(*) FROM user_subscriptions WHERE status = 'active'
                """)

                admin_users = await conn.fetchval("""
                    SELECT COUNT(*) FROM users WHERE is_admin = TRUE
                """)

                total_predictions = await conn.fetchval("SELECT COUNT(*) FROM prediction_history")

                return {
                    'total_users': total_users or 0,
                    'active_users': active_users or 0,
                    'premium_users': premium_users or 0,
                    'admin_users': admin_users or 0,
                    'total_predictions': total_predictions or 0,
                    'total_revenue': 0.0
                }
        except Exception as e:
            logger.error(f"❌ Ошибка статистики: {e}")
            return {}

    async def update_subscription_tier(self, tier_id: int, **kwargs) -> bool:
        try:
            async with self.pool.acquire() as conn:
                updates = []
                params = []
                for key, value in kwargs.items():
                    if value is not None:
                        updates.append(f"{key} = ${len(params) + 1}")
                        params.append(value)

                if not updates:
                    return False

                params.append(tier_id)
                query = f"UPDATE subscription_tiers SET {', '.join(updates)} WHERE id = ${len(params)}"
                await conn.execute(query, *params)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления тарифа: {e}")
            return False


async def init_auth_tables(db):
    pass


async def migrate_existing_users(db):
    pass