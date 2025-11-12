import os
from dotenv import load_dotenv

load_dotenv()

# ======================== BYBIT API ========================
BYBIT_API_BASE = 'https://api.bybit.com'
BYBIT_PUBLIC_ENDPOINT = '/v5/market'

# ======================== DATABASE ========================
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_NAME = os.getenv('DB_NAME', 'pulse_traders')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# MySQL URL - для SQLAlchemy
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ======================== TELEGRAM BOT ========================
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://localhost:5000')

# ======================== JWT ========================
SECRET_KEY = os.getenv('SECRET_KEY', 'change_me')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 720))

# ======================== LSTM SETTINGS ========================
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

# ======================== CACHE SETTINGS ========================
CACHE_TTL = 60  # 5 minutes
PRICE_HISTORY_DAYS = 90

# ======================== 🔐 ADMIN SETTINGS ========================
# Список Telegram ID администраторов
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()] if os.getenv('ADMIN_IDS') else [123456789]

# ======================== 💳 SUBSCRIPTION SETTINGS ========================
DEFAULT_DAILY_LIMIT = 5
DEFAULT_MONTHLY_LIMIT = 30

# Пробные дни (сколько дней бесплатно для новых пользователей)
FREE_TRIAL_DAYS = 7

# ======================== 🎯 PREDICTION LIMITS ========================
# Лимиты для бесплатных пользователей
FREE_DAILY_PREDICTIONS = 5
FREE_MONTHLY_PREDICTIONS = 30

# ======================== POPULAR CRYPTOS (BYBIT SYMBOLS) ========================
# ✨ С ЛОГОТИПАМИ ИЗ COINGECKO
POPULAR_CRYPTOS = [
    {
        'symbol': 'BTCUSDT',
        'name': 'Bitcoin',
        'display_name': 'BTC',
        'emoji': '₿',
        'logo': 'https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png',
        'coingecko_id': 'bitcoin'
    },
    {
        'symbol': 'ETHUSDT',
        'name': 'Ethereum',
        'display_name': 'ETH',
        'emoji': 'Ξ',
        'logo': 'https://coin-images.coingecko.com/coins/images/279/large/ethereum.png',
        'coingecko_id': 'ethereum'
    },
    {
        'symbol': 'BNBUSDT',
        'name': 'Binance Coin',
        'display_name': 'BNB',
        'emoji': '🔶',
        'logo': 'https://coin-images.coingecko.com/coins/images/825/large/bnb-icon2_2x.png',
        'coingecko_id': 'binancecoin'
    },
    {
        'symbol': 'SOLUSDT',
        'name': 'Solana',
        'display_name': 'SOL',
        'emoji': '◎',
        'logo': 'https://coin-images.coingecko.com/coins/images/4128/large/solana.png',
        'coingecko_id': 'solana'
    },
    {
        'symbol': 'XRPUSDT',
        'name': 'Ripple',
        'display_name': 'XRP',
        'emoji': '✘',
        'logo': 'https://coin-images.coingecko.com/coins/images/44/large/xrp-icon.png',
        'coingecko_id': 'ripple'
    },
    {
        'symbol': 'ADAUSDT',
        'name': 'Cardano',
        'display_name': 'ADA',
        'emoji': '✴',
        'logo': 'https://coin-images.coingecko.com/coins/images/975/large/cardano.png',
        'coingecko_id': 'cardano'
    },
]

# ======================== API LIMITS ========================
API_REQUEST_TIMEOUT = 15
MAX_SEARCH_RESULTS = 20

# ======================== LOGGING ========================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'logs/app.log'

os.makedirs('logs', exist_ok=True)

# ======================== PAYMENT SETTINGS ========================
# Для будущей интеграции платежей (Stripe, Yoo.Kassa, etc)
PAYMENT_PROVIDER = os.getenv('PAYMENT_PROVIDER', 'stripe')
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# ======================== EMAIL SETTINGS ========================
# Для отправки уведомлений
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@pulsetraders.com')

# ======================== Google OAuth ========================
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# ======================== Security ========================

MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOGIN_ATTEMPT_TIMEOUT = int(os.getenv('LOGIN_ATTEMPT_TIMEOUT', 300))