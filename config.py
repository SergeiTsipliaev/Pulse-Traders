"""
Configuration for Pulse Traders Application
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ======================== DATABASE ========================
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'pulse_traders')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ======================== SECURITY ========================
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 720))

# ======================== EMAIL SETTINGS ========================
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@pulse-traders.com')

# ======================== GOOGLE OAUTH ========================
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# ======================== TELEGRAM ========================
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://pulse-traders.com')

# ======================== ADMIN SETTINGS ========================
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]

# ======================== APP SETTINGS ========================
APP_PORT = int(os.getenv('APP_PORT', 5000))
APP_HOST = os.getenv('APP_HOST', '0.0.0.0')

# ======================== BYBIT API ========================
BYBIT_API_BASE = 'https://api-testnet.bybit.com'
BYBIT_API_DEMO = 'https://api-demo.bybit.com'
BYBIT_MAIN_NET = 'https://api.bybit.com'

# ======================== CACHE ========================
CACHE_TTL = 300  # 5 минут

# ======================== POPULAR CRYPTOS ========================
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
        'emoji': '⟠',
        'logo': 'https://coin-images.coingecko.com/coins/images/279/large/ethereum.png',
        'coingecko_id': 'ethereum'
    },
    {
        'symbol': 'XRPUSDT',
        'name': 'Ripple',
        'display_name': 'XRP',
        'emoji': '✕',
        'logo': 'https://coin-images.coingecko.com/coins/images/44/large/xrp.png',
        'coingecko_id': 'ripple'
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
        'symbol': 'DOGEUSDT',
        'name': 'Dogecoin',
        'display_name': 'DOGE',
        'emoji': '🐕',
        'logo': 'https://coin-images.coingecko.com/coins/images/5/large/dogecoin.png',
        'coingecko_id': 'dogecoin'
    },
    {
        'symbol': 'AVAXUSDT',
        'name': 'Avalanche',
        'display_name': 'AVAX',
        'emoji': '🔺',
        'logo': 'https://coin-images.coingecko.com/coins/images/9072/large/avalanche-2.png',
        'coingecko_id': 'avalanche-2'
    },
    {
        'symbol': 'LINKUSDT',
        'name': 'Chainlink',
        'display_name': 'LINK',
        'emoji': '🔗',
        'logo': 'https://coin-images.coingecko.com/coins/images/877/large/chainlink-new-logo.png',
        'coingecko_id': 'chainlink'
    },
    {
        'symbol': 'MATICUSDT',
        'name': 'Polygon',
        'display_name': 'MATIC',
        'emoji': '◆',
        'logo': 'https://coin-images.coingecko.com/coins/images/4713/large/matic-token-square.png',
        'coingecko_id': 'matic-network'
    },
    {
        'symbol': 'LTCUSDT',
        'name': 'Litecoin',
        'display_name': 'LTC',
        'emoji': 'Ł',
        'logo': 'https://coin-images.coingecko.com/coins/images/2/large/litecoin.png',
        'coingecko_id': 'litecoin'
    },
    {
        'symbol': 'BCHUSDT',
        'name': 'Bitcoin Cash',
        'display_name': 'BCH',
        'emoji': '₿',
        'logo': 'https://coin-images.coingecko.com/coins/images/780/large/bitcoin-cash-circle.png',
        'coingecko_id': 'bitcoin-cash'
    },
    {
        'symbol': 'UNIUSDT',
        'name': 'Uniswap',
        'display_name': 'UNI',
        'emoji': '🦄',
        'logo': 'https://coin-images.coingecko.com/coins/images/12504/large/uniswap-uni.png',
        'coingecko_id': 'uniswap'
    },
    {
        'symbol': 'XLMUSDT',
        'name': 'Stellar',
        'display_name': 'XLM',
        'emoji': '⭐',
        'logo': 'https://coin-images.coingecko.com/coins/images/100/large/stellar.png',
        'coingecko_id': 'stellar'
    },
    {
        'symbol': 'XMUSDT',
        'name': 'NEM',
        'display_name': 'XEM',
        'emoji': '※',
        'logo': 'https://coin-images.coingecko.com/coins/images/15/large/nem.png',
        'coingecko_id': 'nem'
    },
    {
        'symbol': 'ETCUSDT',
        'name': 'Ethereum Classic',
        'display_name': 'ETC',
        'emoji': '♦',
        'logo': 'https://coin-images.coingecko.com/coins/images/453/large/ethereum-classic-icon.png',
        'coingecko_id': 'ethereum-classic'
    },
    {
        'symbol': 'TRXUSDT',
        'name': 'TRON',
        'display_name': 'TRX',
        'emoji': '◉',
        'logo': 'https://coin-images.coingecko.com/coins/images/1094/large/tron-logo.png',
        'coingecko_id': 'tron'
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
PAYMENT_PROVIDER = os.getenv('PAYMENT_PROVIDER', 'stripe')
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# ======================== Security ========================
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOGIN_ATTEMPT_TIMEOUT = int(os.getenv('LOGIN_ATTEMPT_TIMEOUT', 300))

DEFAULT_SUBSCRIPTION_TIER = 'starter'

ux_mode: 'popup'