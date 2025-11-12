import aiomysql
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Database:
    """Асинхронный класс для работы с MySQL через aiomysql"""

    def __init__(self, connection_string: str):
        # Парсим MySQL URL
        # Формат: mysql+aiomysql://user:password@host:port/database
        # Или: mysql://user:password@host:port/database

        self.connection_string = connection_string
        self.pool = None
        self.is_connected = False
        self.db_config = self._parse_connection_string(connection_string)

    def _parse_connection_string(self, url: str) -> dict:
        """Парсит MySQL URL с поддержкой спецсимволов в пароле"""
        from urllib.parse import urlparse

        # Обработка разных форматов
        if url.startswith('mysql+aiomysql://'):
            url = url.replace('mysql+aiomysql://', 'mysql://')

        parsed = urlparse(url)

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'user': parsed.username or 'root',
            'password': parsed.password or '',
            'db': parsed.path.lstrip('/') or 'pulse_traders'
        }

    async def connect(self) -> bool:
        """Асинхронное подключение к БД"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                db=self.db_config['db'],
                minsize=5,
                maxsize=20
            )
            self.is_connected = True
            await self.create_tables()
            logger.info("✅ MySQL пул подключений установлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения MySQL: {e}")
            self.is_connected = False
            return False

    async def close(self):
        """Закрытие пула подключений"""
        try:
            if self.pool:
                self.pool.close()
                await self.pool.wait_closed()
                self.is_connected = False
                logger.info("✅ БД пул подключений закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия пула: {e}")

    async def create_tables(self):
        """Создание таблиц если их нет"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # КРИПТОВАЛЮТЫ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS cryptocurrencies (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            symbol VARCHAR(20) UNIQUE NOT NULL,
                            name VARCHAR(100) NOT NULL,
                            display_name VARCHAR(10),
                            emoji VARCHAR(5),
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        )
                    """)

                    # ИСТОРИЯ ЦЕН
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS price_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            symbol VARCHAR(20) NOT NULL,
                            price DECIMAL(20, 8) NOT NULL,
                            change_24h DECIMAL(10, 2),
                            volume_24h DECIMAL(20, 2),
                            high_24h DECIMAL(20, 8),
                            low_24h DECIMAL(20, 8),
                            timestamp TIMESTAMP NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (symbol) REFERENCES cryptocurrencies(symbol) ON DELETE CASCADE,
                            INDEX idx_symbol (symbol)
                        )
                    """)

                    # ПОЛЬЗОВАТЕЛИ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            telegram_id BIGINT UNIQUE NOT NULL,
                            username VARCHAR(100),
                            first_name VARCHAR(100),
                            last_name VARCHAR(100),
                            email VARCHAR(255),
                            password_hash VARCHAR(255),
                            is_admin BOOLEAN DEFAULT FALSE,
                            is_banned BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_telegram_id (telegram_id)
                        )
                    """)

                    # ТАРИФЫ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS subscription_tiers (
                            id INT AUTO_INCREMENT PRIMARY KEY,
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
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        )
                    """)

                    # ПОДПИСКИ ПОЛЬЗОВАТЕЛЕЙ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS user_subscriptions (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL UNIQUE,
                            tier_id INT NOT NULL,
                            status VARCHAR(50) DEFAULT 'active',
                            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP,
                            next_billing_date TIMESTAMP,
                            payment_method VARCHAR(50),
                            auto_renew BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            FOREIGN KEY (tier_id) REFERENCES subscription_tiers(id) ON DELETE SET NULL
                        )
                    """)

                    # ЛИМИТЫ ПРЕДСКАЗАНИЙ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS prediction_limits (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL UNIQUE,
                            predictions_used_today INT DEFAULT 0,
                            predictions_used_month INT DEFAULT 0,
                            predictions_limit_daily INT DEFAULT 5,
                            predictions_limit_monthly INT DEFAULT 30,
                            is_premium BOOLEAN DEFAULT FALSE,
                            free_tier_used BOOLEAN DEFAULT FALSE,
                            last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """)

                    # ИСТОРИЯ ПРЕДСКАЗАНИЙ
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS prediction_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            symbol VARCHAR(20) NOT NULL,
                            predicted_price DECIMAL(20, 8),
                            confidence DECIMAL(5, 2),
                            signal VARCHAR(50),
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            FOREIGN KEY (symbol) REFERENCES cryptocurrencies(symbol) ON DELETE CASCADE,
                            INDEX idx_user_id (user_id)
                        )
                    """)

                    logger.info("✅ Все таблицы БД созданы/проверены")
                    await conn.commit()

        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")

    # ==================== КРИПТОВАЛЮТЫ ====================

    async def add_cryptocurrency(self, symbol: str, name: str, display_name: str, emoji: str = "") -> bool:
        """Добавление криптовалюты в БД"""
        if not self.is_connected:
            return False

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO cryptocurrencies (symbol, name, display_name, emoji)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            name = VALUES(name),
                            display_name = VALUES(display_name),
                            emoji = VALUES(emoji),
                            updated_at = CURRENT_TIMESTAMP
                    """, (symbol, name, display_name, emoji))
                    await conn.commit()
                    logger.debug(f"💾 Сохранена криптовалюта: {symbol}")
                    return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления: {e}")
            return False

    async def get_all_cryptocurrencies(self) -> List[Dict]:
        """Получение всех активных криптовалют"""
        if not self.is_connected:
            return []

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT id, symbol, name, display_name, emoji
                        FROM cryptocurrencies
                        WHERE is_active = TRUE
                        ORDER BY symbol
                    """)
                    results = await cursor.fetchall()
                    logger.debug(f"📋 Загружено: {len(results)} криптовалют")
                    return results
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка: {e}")
            return []

    async def search_cryptocurrencies(self, query: str) -> List[Dict]:
        """Поиск криптовалют"""
        if not self.is_connected:
            return []

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT id, symbol, name, display_name, emoji
                        FROM cryptocurrencies
                        WHERE 
                            UPPER(symbol) = UPPER(%s) OR
                            UPPER(symbol) LIKE UPPER(%s) OR
                            UPPER(name) LIKE UPPER(%s)
                        ORDER BY 
                            CASE WHEN UPPER(symbol) = UPPER(%s) THEN 1
                                 WHEN UPPER(symbol) LIKE UPPER(%s) THEN 2
                                 ELSE 3
                            END,
                            symbol
                        LIMIT 20
                    """, (query, f"%{query}%", f"%{query}%", query, f"%{query}%"))
                    results = await cursor.fetchall()
                    logger.debug(f"🔍 Найдено: {len(results)} результатов для '{query}'")
                    return results
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    # ==================== ТАРИФЫ ====================

    async def get_all_subscription_tiers(self) -> List[Dict]:
        """Получить все тарифы"""
        if not self.is_connected:
            return []

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT * FROM subscription_tiers
                        WHERE is_active = TRUE
                        ORDER BY display_order
                    """)
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Ошибка получения тарифов: {e}")
            return []

    async def create_subscription_tier(self, name: str, display_name: str, price: float,
                                       monthly_predictions: int, daily_predictions: int,
                                       features: str = "", description: str = "",
                                       display_order: int = 0) -> Dict:
        """Создать новый тариф"""
        if not self.is_connected:
            return None

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        INSERT INTO subscription_tiers 
                        (name, display_name, price, monthly_predictions, daily_predictions, 
                         features, description, display_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, display_name, price, monthly_predictions, daily_predictions,
                          features, description, display_order))
                    await conn.commit()

                    # Возвращаем созданный объект
                    tier_id = cursor.lastrowid
                    await cursor.execute("SELECT * FROM subscription_tiers WHERE id = %s", (tier_id,))
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Ошибка создания тарифа: {e}")
            return None