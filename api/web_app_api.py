import asyncio
import logging
import httpx
import os
import json
import time
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.auth_routes import verify_jwt_token
from config import POPULAR_CRYPTOS, CACHE_TTL, DATABASE_URL, ADMIN_IDS
from services import bybit_service
from models.database import Database
from api import auth_routes  # ✨ НОВОЕ
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from api import admin_routes, user_routes
from json import JSONEncoder

# class DateTimeEncoder(JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, datetime):
#             return obj.isoformat()
#         return super().default(obj)


# Глобальная переменная БД
db: Optional[Database] = None

# 🪙 Глобальный кэш криптовалют из JSON
CRYPTOS_DATA = {}
CRYPTOS_FILE = Path('data/cryptos.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

cache = {}


# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ JSON КЭША ====================

async def load_cryptos_from_file():
    """Загружает список всех криптовалют из JSON файла при старте приложения"""
    global CRYPTOS_DATA

    try:
        if CRYPTOS_FILE.exists():
            with open(CRYPTOS_FILE, 'r', encoding='utf-8') as f:
                CRYPTOS_DATA = json.load(f)
            logger.info(f"✅ Загружено {len(CRYPTOS_DATA)} криптовалют из {CRYPTOS_FILE}")
            return True
        else:
            logger.warning(f"⚠️ Файл {CRYPTOS_FILE} не найден")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки криптовалют: {e}")
        return False


def get_crypto_logo_from_config(symbol: str):
    """Получить логотип криптовалюты - сначала конфиг, потом JSON"""
    # 1️⃣ Сначала ищем в конфиге
    for crypto in POPULAR_CRYPTOS:
        if crypto['symbol'] == symbol:
            return {
                'logo': crypto.get('logo', ''),
                'emoji': crypto.get('emoji', '💰'),
                'name': crypto.get('name', ''),
                'display_name': crypto.get('display_name', ''),
                'source': 'config'
            }

    # 2️⃣ ДЛЯ ОСТАЛЬНЫХ - ищем в JSON кэше
    symbol_clean = symbol.replace('USDT', '').upper()

    if symbol_clean in CRYPTOS_DATA:
        crypto_data = CRYPTOS_DATA[symbol_clean]
        return {
            'logo': crypto_data.get('logo', ''),
            'emoji': '💰',
            'name': crypto_data.get('name', symbol_clean),
            'display_name': symbol_clean,
            'source': 'json_cache'
        }

    return None


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global db

    logger.info("🚀 Запуск приложения...")

    # ✨ Загружаем JSON с криптовалютами
    logger.info("📥 Загружаем список криптовалют из JSON...")
    if not await load_cryptos_from_file():
        logger.warning("⚠️ Не удалось загрузить крипто, будет использоваться дефолт")

    # Подключаемся к БД
    db = Database(DATABASE_URL)
    if await db.connect():
        logger.info("✅ БД подключена")

        # ✨ НОВОЕ: Инициализируем таблицы аутентификации
        logger.info("🔐 Инициализация таблиц аутентификации...")
        from models.database import init_auth_tables, migrate_existing_users
        await init_auth_tables(db)
        await migrate_existing_users(db)
        logger.info("✅ Аутентификация готова")

        # Добавляем популярные криптовалюты
        for crypto in POPULAR_CRYPTOS:
            await db.add_cryptocurrency(
                symbol=crypto['symbol'],
                name=crypto['name'],
                display_name=crypto['display_name'],
                emoji=crypto['emoji']
            )

        # Инициализируем тарифы подписок
        logger.info("💳 Инициализация тарифов подписок...")
        tiers = await db.get_all_subscription_tiers()
        if len(tiers) == 0:
            logger.info("📝 Создание стандартных тарифов...")

            await db.create_subscription_tier(
                name='starter',
                display_name='Starter',
                price=4.99,
                monthly_predictions=100,
                daily_predictions=10,
                features='Базовые прогнозы, техподдержка',
                description='Начальный пакет для новичков',
                display_order=1
            )

            await db.create_subscription_tier(
                name='pro',
                display_name='Pro',
                price=9.99,
                monthly_predictions=300,
                daily_predictions=25,
                features='Продвинутые прогнозы, приоритет, аналитика',
                description='Для активных трейдеров',
                display_order=2
            )

            await db.create_subscription_tier(
                name='enterprise',
                display_name='Enterprise',
                price=29.99,
                monthly_predictions=999,
                daily_predictions=99,
                features='Неограниченные прогнозы, API, консультации',
                description='Для профессионалов',
                display_order=3
            )

            logger.info("✅ Тарифы созданы")
    else:
        logger.warning("⚠️ БД недоступна")

    logger.info("✅ Приложение готово")

    yield

    logger.info("🛑 Остановка приложения...")
    if db:
        await db.close()
    await bybit_service.close_session()
    logger.info("✅ Приложение остановлено")


# ==================== APP ====================

app = FastAPI(title="PulseTrade Bot", version="2.0.0", lifespan=lifespan)

static_dir = Path("static")
if static_dir.exists() and static_dir.is_dir():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Статические файлы загружены")

# ✨ ДОБАВЛЯЕМ ADMIN И USER ROUTERS
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(user_routes.router)


# Передаем db в router контекст
@app.middleware("http")
async def add_db_to_state(request: Request, call_next):
    request.state.db = db
    response = await call_next(request)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_cache(key: str):
    if key in cache:
        value, timestamp = cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return value
    return None


async def set_cache(key: str, value):
    cache[key] = (value, time.time())


async def verify_token(authorization: str = Header(None)):
    """Проверить JWT токен из header Authorization"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        payload = verify_jwt_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

# ==================== MIDDLEWARE ДЛЯ ПЕРЕДАЧИ DB ====================

@app.middleware("http")
async def inject_db(request: Request, call_next):
    """Добавляем db в параметры функций через зависимости"""
    request.state.db = db
    response = await call_next(request)
    return response


def get_db_dependency():
    """Зависимость для получения db в endpoints"""
    return db


# ==================== ОСНОВНЫЕ ENDPOINTS ====================

@app.get('/')
async def index():
    """Главная страница - перенаправляем на login если не авторизован"""
    try:
        # Проверяем есть ли токен в cookie или header
        return FileResponse("static/index.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading app"})



@app.get('/api/auth/me')
async def get_current_user(authorization: str = Header(None), db=None):
    """Получить текущего пользователя"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        scheme, token = authorization.split()
        payload = verify_jwt_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = int(payload.get('sub'))

        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")

        user = await db.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return JSONResponse({
            'success': True,
            'data': user
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/auth.html')
async def auth_page():
    """Страница авторизации"""
    try:
        return FileResponse("static/auth.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/auth')
async def auth_redirect_handler():
    """Обработчик редиректов с авторизации"""
    from fastapi.responses import HTMLResponse

    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Авторизация - Pulse Traders</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            h1 { color: #333; margin-top: 0; }
            p { color: #666; }
            .error { color: #c33; background: #fee; padding: 12px; border-radius: 8px; margin-top: 20px; }
            .success { color: #3c3; background: #efe; padding: 12px; border-radius: 8px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner"></div>
            <h1>Авторизация...</h1>
            <p id="message">Пожалуйста, подождите</p>
            <div id="status"></div>
        </div>

        <script>
            function handleAuthRedirect() {
                const params = new URLSearchParams(window.location.search);
                const token = params.get('token');
                const userId = params.get('user_id');
                const error = params.get('error');

                const messageEl = document.getElementById('message');
                const statusEl = document.getElementById('status');

                if (error) {
                    const errorMsg = decodeURIComponent(error);
                    messageEl.textContent = 'Ошибка авторизации';
                    statusEl.innerHTML = `<div class="error"><strong>Ошибка:</strong> ${errorMsg}</div>`;
                    setTimeout(() => { window.location.href = '/auth.html'; }, 3000);
                    return;
                }

                if (token && userId) {
                    localStorage.setItem('auth_token', token);
                    localStorage.setItem('user_id', userId);
                    sessionStorage.setItem('auth_token', token);

                    messageEl.textContent = 'Авторизация успешна!';
                    statusEl.innerHTML = '<div class="success">✅ Вы успешно вошли. Переводим...</div>';
                    setTimeout(() => { window.location.href = '/dashboard'; }, 1500);
                    return;
                }

                messageEl.textContent = 'Нет данных авторизации';
                statusEl.innerHTML = '<div class="error">Параметры авторизации не найдены</div>';
                setTimeout(() => { window.location.href = '/auth.html'; }, 2000);
            }

            window.addEventListener('DOMContentLoaded', handleAuthRedirect);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get('/favicon.ico')
async def favicon():
    """Фавикон браузера"""
    try:
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")
    except Exception as e:
        logger.error(f"Error: {e}")
        return FileResponse("static/favicon.svg", media_type="image/svg+xml", status_code=404)


@app.get('/auth-terms')
async def auth_terms():
    """Статическая версия условий"""
    try:
        return FileResponse("static/auth-terms.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/auth-privacy')
async def auth_privacy():
    """Статическая версия политики"""
    try:
        return FileResponse("static/auth-privacy.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/admin-panel.html')
async def admin_panel():
    """Админ-панель (требует авторизации)"""
    try:
        return FileResponse("static/admin-panel.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/user-profile.html')
async def user_profile():
    """Личный кабинет (требует авторизации)"""
    try:
        return FileResponse("static/user-profile.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/crypto-detail.html')
async def crypto_detail():
    try:
        return FileResponse("static/crypto-detail.html", media_type="text/html")
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Error loading page"})


@app.get('/api/health')
async def health_check():
    db_status = "connected" if db and db.is_connected else "disconnected"
    return JSONResponse({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': db_status,
        'api': 'Bybit API v5',
    })


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@app.post('/api/auth/register')
async def register_user(request: Request, x_user_id: int = Header(None)):
    """Регистрация/инициализация пользователя из Telegram"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        body = await request.json()

        user = await db.get_or_create_user(
            telegram_id=body.get('telegram_id', x_user_id),
            username=body.get('username', ''),
            first_name=body.get('first_name', ''),
            last_name=body.get('last_name', '')
        )

        if not user:
            raise HTTPException(status_code=400, detail="Failed to create user")

        return JSONResponse({
            'success': True,
            'data': user
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== КРИПТОВАЛЮТЫ ====================

@app.get('/api/search')
async def search_cryptocurrencies(q: str = Query('', min_length=1)):
    query = q.strip()

    if not query:
        return JSONResponse({'success': True, 'data': [], 'source': 'empty'})

    cache_key = f"search:{query}"
    cached_result = await get_cache(cache_key)
    if cached_result:
        return JSONResponse(cached_result)

    try:
        if db and db.is_connected:
            db_results = await db.search_cryptocurrencies(query)
            if db_results:
                for crypto in db_results:
                    logo_info = get_crypto_logo_from_config(f"{crypto['symbol']}USDT")
                    if logo_info:
                        crypto['logo'] = logo_info.get('logo', '')
                        crypto['emoji'] = logo_info.get('emoji', '💰')

                result = {'success': True, 'data': db_results, 'source': 'database', 'count': len(db_results)}
                await set_cache(cache_key, result)
                return JSONResponse(result)

        api_results = await bybit_service.search_cryptocurrencies(query)

        for crypto in api_results:
            symbol = crypto.get('symbol', '')
            logo_info = get_crypto_logo_from_config(symbol)
            if logo_info:
                crypto['logo'] = logo_info.get('logo', '')
                crypto['emoji'] = logo_info.get('emoji', '💰')

        result = {'success': True, 'data': api_results, 'source': 'bybit_api', 'count': len(api_results)}
        await set_cache(cache_key, result)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Search error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e), 'data': []})


@app.get('/api/cryptos/all')
async def get_all_cryptocurrencies():
    try:
        cache_key = "all_cryptos"
        cached_result = await get_cache(cache_key)
        if cached_result:
            return JSONResponse(cached_result)

        result = {'success': True, 'data': POPULAR_CRYPTOS, 'total': len(POPULAR_CRYPTOS), 'source': 'config'}
        await set_cache(cache_key, result)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e), 'data': []})


@app.get('/api/crypto/{symbol}')
async def get_crypto_data(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    cache_key = f"crypto:{symbol}"
    cached_result = await get_cache(cache_key)
    if cached_result:
        return JSONResponse(cached_result)

    try:
        ticker = await bybit_service.get_current_price(symbol)
        if not ticker:
            raise HTTPException(status_code=404, detail=f'Failed to get data')

        history = await bybit_service.get_price_history(symbol, days=90)
        if not history:
            history = {'prices': [ticker['last_price']], 'timestamps': [int(time.time() * 1000)]}

        prices = history['prices']
        indicators = await bybit_service.calculate_technical_indicators(prices)

        rsi = calculate_rsi(np.array(prices))
        ma_7 = np.mean(np.array(prices[-7:]))
        ma_25 = np.mean(np.array(prices[-25:]))
        ma_50 = np.mean(np.array(prices[-50:]))
        volatility = calculate_volatility(np.array(prices))
        trend_strength = calculate_trend_strength(np.array(prices))

        logo_info = get_crypto_logo_from_config(symbol)

        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'logo': logo_info.get('logo', '') if logo_info else '',
                'emoji': logo_info.get('emoji', '💰') if logo_info else '💰',
                'name': logo_info.get('name', symbol.replace('USDT', '')) if logo_info else symbol.replace('USDT', ''),
                'display_name': logo_info.get('display_name',
                                              symbol.replace('USDT', '')) if logo_info else symbol.replace('USDT', ''),
                'current': {
                    'price': ticker['last_price'],
                    'change_24h': ticker['change_24h'],
                    'high_24h': ticker['high_24h'],
                    'low_24h': ticker['low_24h'],
                    'volume_24h': ticker['volume_24h'],
                    'turnover_24h': ticker['turnover_24h']
                },
                'history': {
                    'prices': prices,
                    'timestamps': history['timestamps']
                },
                'indicators': {
                    'rsi': float(rsi),
                    'ma_7': float(ma_7),
                    'ma_25': float(ma_25),
                    'ma_50': float(ma_50),
                    'volatility': float(volatility),
                    'trend_strength': float(trend_strength)
                }
            },
            'timestamp': datetime.now().isoformat()
        }

        await set_cache(cache_key, result)
        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/predict/{symbol}')
async def predict_price(symbol: str, request: Request):
    """Прогноз цены с проверкой лимитов"""
    authorization = request.headers.get('Authorization')

    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        scheme, token = authorization.split()
        payload = verify_jwt_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        x_user_id = int(payload.get('sub'))
    except:
        raise HTTPException(status_code=401, detail="Unauthorized")

    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # ✨ ПРОВЕРЯЕМ ЛИМИТ
        limits = await db.check_prediction_limit(x_user_id)
        if not limits:
            raise HTTPException(status_code=404, detail="Limits not found")

        daily_remaining = limits['predictions_limit_daily'] - limits['predictions_used_today']

        if daily_remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    'success': False,
                    'error': 'Daily limit reached',
                    'message': 'Вы исчерпали дневной лимит. Попробуйте завтра или купите подписку.',
                    'needs_premium': True
                }
            )

        from models.lstm_model import predictor

        history = await bybit_service.get_price_history(symbol, days=90)
        if not history or not history['prices']:
            raise HTTPException(status_code=400, detail='Insufficient data')

        prices = np.array(history['prices'], dtype=float)
        current_price = prices[-1]

        predictions, ensemble_confidence, details = predictor.ensemble_prediction(prices, future_steps=7)
        expected_price = predictions[-1]

        support, resistance = calculate_support_resistance(prices)

        trend = (expected_price - current_price) / current_price * 100
        signal, signal_text, emoji = get_trading_signal(trend, prices)

        confidence = calculate_confidence(current_price, expected_price, support, resistance, trend, prices)

        # ✨ СОХРАНЯЕМ ПРОГНОЗ В ИСТОРИЮ
        await db.save_prediction(
            user_id=x_user_id,
            symbol=symbol,
            predicted_price=float(expected_price),
            confidence=float(confidence),
            signal=signal
        )

        # Получаем обновленные лимиты
        updated_limits = await db.check_prediction_limit(x_user_id)

        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'current_price': float(current_price),
                'expected_price': float(expected_price),
                'predictions': [float(p) for p in predictions],
                'predicted_change': float(trend),
                'support': float(support),
                'resistance': float(resistance),
                'signal': signal,
                'signal_text': signal_text,
                'signal_emoji': emoji,
                'confidence': float(confidence),
                'days': 7,
                'rmse': calculate_rmse(prices),
                'limits': {
                    'daily': {
                        'used': updated_limits['predictions_used_today'],
                        'remaining': max(0, updated_limits['predictions_limit_daily'] - updated_limits[
                            'predictions_used_today'])
                    },
                    'monthly': {
                        'used': updated_limits['predictions_used_month'],
                        'remaining': max(0, updated_limits['predictions_limit_monthly'] - updated_limits[
                            'predictions_used_month'])
                    }
                }
            },
            'timestamp': datetime.now().isoformat()
        }

        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/klines/{symbol}')
async def get_klines(
        symbol: str,
        interval: str = Query('60', description="Интервал свечей"),
        limit: int = Query(200, ge=1, le=1000, description="Лимит свечей")
):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    try:
        klines = await bybit_service.get_kline_data(symbol, interval, limit)
        if not klines:
            raise HTTPException(status_code=404, detail='Failed to get klines')

        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })

        return JSONResponse({
            'success': True,
            'data': formatted_klines,
            'symbol': symbol,
            'interval': interval,
            'count': len(formatted_klines)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    try:
        if len(prices) < period:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs >= 0 else 50

        return float(rsi)
    except:
        return 50.0


def calculate_volatility(prices: np.ndarray) -> float:
    try:
        if len(prices) < 2:
            return 0.0
        returns = np.diff(prices) / prices[:-1] * 100
        return float(np.std(returns))
    except:
        return 0.0


def calculate_trend_strength(prices: np.ndarray) -> float:
    try:
        if len(prices) < 2:
            return 0.0
        first = prices[0]
        last = prices[-1]
        trend = (last - first) / first * 100
        return float(trend)
    except:
        return 0.0


def calculate_support_resistance(prices: np.ndarray) -> tuple:
    try:
        high_20 = np.max(prices[-20:])
        low_20 = np.min(prices[-20:])
        return float(low_20), float(high_20)
    except:
        current = prices[-1]
        return float(current * 0.95), float(current * 1.05)


def calculate_confidence(current_price: float, expected_price: float,
                         support: float, resistance: float,
                         trend: float, prices: np.ndarray) -> float:
    try:
        if len(prices) < 30:
            return 25.0

        returns = np.diff(prices) / prices[:-1] * 100
        volatility = np.std(returns)
        volatility_score = max(0, 100 - (volatility * 5))
        volatility_score = min(100, volatility_score)

        rsi = calculate_rsi(prices)
        rsi_diff = abs(rsi - 50)
        rsi_score = max(0, 100 - (rsi_diff * 1.5))
        if rsi > 75 or rsi < 25:
            rsi_score = rsi_score * 0.6

        support_resistance_range = resistance - support
        if support_resistance_range == 0:
            sr_score = 50
        else:
            position = (expected_price - support) / support_resistance_range
            if 0 <= position <= 1:
                sr_score = 85
            elif position > 1:
                sr_score = 55 - (position - 1) * 10
            else:
                sr_score = 55 - abs(position) * 10
            sr_score = max(20, min(100, sr_score))

        trend_7 = (prices[-1] - prices[-7]) / prices[-7] * 100 if len(prices) >= 7 else 0
        trend_14 = (prices[-1] - prices[-14]) / prices[-14] * 100 if len(prices) >= 14 else 0
        trend_30 = (prices[-1] - prices[-30]) / prices[-30] * 100 if len(prices) >= 30 else 0

        trend_consistency = 0
        if (trend_7 > 0 and trend_14 > 0 and trend_30 > 0) or \
                (trend_7 < 0 and trend_14 < 0 and trend_30 < 0):
            trend_consistency = 90
        elif (trend_7 > 0 and trend_14 > 0) or (trend_7 < 0 and trend_14 < 0):
            trend_consistency = 70
        else:
            trend_consistency = 40

        predicted_change = abs((expected_price - current_price) / current_price * 100)

        if predicted_change < 0.5:
            change_score = 30
        elif predicted_change < 2:
            change_score = 50
        elif predicted_change < 5:
            change_score = 75
        else:
            change_score = 85

        trend_agreement = 0
        if trend > 0 and expected_price > current_price:
            trend_agreement = 90
        elif trend < 0 and expected_price < current_price:
            trend_agreement = 90
        elif abs(trend) < 1:
            trend_agreement = 70
        else:
            trend_agreement = 40

        confidence = (
                volatility_score * 0.20 +
                rsi_score * 0.20 +
                sr_score * 0.15 +
                trend_consistency * 0.20 +
                change_score * 0.10 +
                trend_agreement * 0.15
        )

        confidence = max(25, min(95, confidence))
        return float(confidence)

    except Exception as e:
        logger.error(f"Error: {e}")
        return 50.0


def get_trading_signal(trend: float, prices: np.ndarray) -> tuple:
    rsi = calculate_rsi(prices)

    if trend > 10 and rsi < 70:
        return 'STRONG_BUY', '🟢 Сильно покупать', '🟢'
    elif trend > 3 and rsi < 70:
        return 'BUY', '🟢 Покупать', '🟢'
    elif -3 <= trend <= 3 and 30 < rsi < 70:
        return 'HOLD', '🟡 Удерживать', '🟡'
    elif trend < -3 and rsi > 30:
        return 'SELL', '🔴 Продавать', '🔴'
    elif trend < -10 and rsi > 30:
        return 'STRONG_SELL', '🔴 Сильно продавать', '🔴'
    else:
        return 'HOLD', '🟡 Удерживать', '🟡'


def calculate_rmse(prices: np.ndarray) -> float:
    try:
        if len(prices) < 2:
            return 0.0
        returns = np.diff(prices) / prices[:-1]
        rmse = np.std(returns) * prices[-1]
        return max(0, float(rmse))
    except:
        return 0.0


if __name__ == '__main__':
    import uvicorn

    port = int(os.environ.get('PORT', 5000))
    uvicorn.run("api.web_app_api:app", host='0.0.0.0', port=port)