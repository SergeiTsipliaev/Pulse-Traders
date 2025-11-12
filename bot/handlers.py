from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
from aiogram.filters import Command
import logging

from config import WEB_APP_URL, ADMIN_IDS
from models.database import Database

logger = logging.getLogger(__name__)

router = Router()

# Глобальная БД (будет инициализирована в main.py)
db: Database = None


def set_db(database: Database):
    """Установить глобальную БД"""
    global db
    db = database


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""

    # ✨ НОВОЕ: Регистрируем или обновляем пользователя в БД
    if db and db.is_connected:
        user = await db.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username or '',
            first_name=message.from_user.first_name or '',
            last_name=message.from_user.last_name or ''
        )
        logger.info(f"✅ Пользователь {message.from_user.id} зарегистрирован: {user}")

    # Определяем кнопки в зависимости от статуса пользователя
    is_admin = message.from_user.id in ADMIN_IDS

    buttons = [
        [InlineKeyboardButton(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )],
    ]

    # Если админ - добавляем кнопку админ-панели
    if is_admin:
        buttons.append([
            InlineKeyboardButton(
                text="🔧 Админ-панель",
                web_app=WebAppInfo(url=f"{WEB_APP_URL}/admin-panel.html")
            )
        ])

    # Добавляем кнопку профиля
    buttons.append([
        InlineKeyboardButton(
            text="👤 Мой профиль",
            web_app=WebAppInfo(url=f"{WEB_APP_URL}/user-profile.html")
        )
    ])

    # Кнопка помощи
    buttons.append([
        InlineKeyboardButton(
            text="ℹ️ О приложении",
            callback_data="about"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    welcome_text = (
        "🚀 <b>Crypto LSTM Predictor</b>\n\n"
        "Искусственный интеллект для прогнозирования криптовалют!\n\n"
        "🧠 <b>Технология:</b> LSTM нейронная сеть\n"
        "📊 <b>Точность:</b> До 85%\n"
        "⏰ <b>Прогноз:</b> До 7 дней\n\n"
    )

    if is_admin:
        welcome_text += "👑 <b>Статус: Администратор</b>\n"
        welcome_text += "Вы можете управлять пользователями и тарифами в админ-панели.\n\n"

    welcome_text += "Нажмите кнопку ниже, чтобы открыть приложение:"

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    logger.info(f"✅ Пользователь {message.from_user.id} запустил /start")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help"""

    help_text = (
        "📱 <b>Crypto LSTM Predictor</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/start - Запустить бота\n"
        "/help - Справка\n"
        "/about - Информация о приложении\n"
        "/limits - Проверить лимиты\n\n"
        "<b>Возможности:</b>\n"
        "• 📈 Прогноз цен на 1-7 дней\n"
        "• 🧠 LSTM нейронная сеть\n"
        "• 📊 Технический анализ (RSI, MA, волатильность)\n"
        "• 📉 Интерактивные графики\n"
        "• 🎯 Торговые сигналы\n"
        "• 📱 Адаптивный дизайн\n"
        "• 💳 Система подписок\n\n"
        "<b>Поддерживаемые криптовалюты:</b>\n"
        "Bitcoin (BTC), Ethereum (ETH), Binance Coin (BNB), "
        "Solana (SOL), Ripple (XRP) и 15000+ других\n\n"
        "<b>Система лимитов:</b>\n"
        "🆓 Бесплатно: 5 прогнозов в день, 30 в месяц\n"
        "💳 Premium: до 99 прогнозов в день\n"
        "∞ Enterprise: неограниченные прогнозы"
    )

    await message.answer(help_text, parse_mode="HTML")
    logger.info(f"✅ Пользователь {message.from_user.id} запросил /help")


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    """Обработчик команды /about"""

    about_text = (
        "📱 <b>Crypto LSTM Predictor</b>\n\n"
        "<b>Что это?</b>\n"
        "Приложение для анализа и прогноза цен криптовалют на основе "
        "нейронной сети LSTM (Long Short-Term Memory).\n\n"
        "<b>Возможности:</b>\n"
        "• 📈 Прогноз цен на 1-7 дней\n"
        "• 🧠 Анализ 90 дней истории цен\n"
        "• 📊 Технический анализ (RSI, MA, волатильность)\n"
        "• 📉 Интерактивные графики в реальном времени\n"
        "• 🎯 Торговые сигналы (BUY, HOLD, SELL)\n"
        "• 📱 Адаптивный дизайн (работает везде)\n"
        "• 💳 Гибкая система подписок\n\n"
        "<b>Поддерживаемые криптовалюты:</b>\n"
        "15000+ криптовалют с CoinGecko!\n\n"
        "<b>Точность:</b>\n"
        "До 85% благодаря ensemble методам\n\n"
        "<b>Разработчик:</b> Pulse Traders Team\n"
        "<b>Версия:</b> 2.0.0\n"
        "<b>Сайт:</b> https://pulsetraders.com"
    )

    await message.answer(about_text, parse_mode="HTML")
    logger.info(f"✅ Пользователь {message.from_user.id} запросил /about")


@router.message(Command("limits"))
async def cmd_limits(message: Message) -> None:
    """Проверить текущие лимиты на прогнозы"""

    if not db or not db.is_connected:
        await message.answer("❌ БД недоступна. Попробуйте позже.")
        return

    try:
        limits = await db.check_prediction_limit(message.from_user.id)

        if not limits:
            # Пользователь не найден в БД лимитов
            await message.answer("❌ Информация о вас не найдена. Откройте приложение для регистрации.")
            return

        daily_remaining = limits['predictions_limit_daily'] - limits['predictions_used_today']
        monthly_remaining = limits['predictions_limit_monthly'] - limits['predictions_used_month']

        tier_status = "💎 Premium" if limits['is_premium'] else "🆓 Бесплатный"

        limits_text = (
            f"📊 <b>Ваши лимиты на прогнозы</b>\n\n"
            f"<b>Статус:</b> {tier_status}\n\n"
            f"<b>Прогнозы в день:</b>\n"
            f"  📊 Использовано: {limits['predictions_used_today']}/{limits['predictions_limit_daily']}\n"
            f"  📊 Осталось: {max(0, daily_remaining)}\n\n"
            f"<b>Прогнозы в месяц:</b>\n"
            f"  📊 Использовано: {limits['predictions_used_month']}/{limits['predictions_limit_monthly']}\n"
            f"  📊 Осталось: {max(0, monthly_remaining)}\n\n"
        )

        if daily_remaining <= 0:
            limits_text += "⚠️ <b>Дневной лимит исчерпан!</b>\n"
            limits_text += "Попробуйте завтра или купите подписку.\n\n"

        if monthly_remaining <= 0:
            limits_text += "⚠️ <b>Месячный лимит исчерпан!</b>\n"
            limits_text += "Купите подписку для продолжения.\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Выбрать подписку",
                web_app=WebAppInfo(url=f"{WEB_APP_URL}/user-profile.html")
            )]
        ])

        await message.answer(limits_text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error checking limits: {e}")
        await message.answer("❌ Ошибка проверки лимитов")


@router.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery) -> None:
    """Информация о приложении (из инлайн кнопки)"""

    await callback.answer("ℹ️ Загружение информации...", show_alert=False)

    about_text = (
        "📱 <b>Crypto LSTM Predictor</b>\n\n"
        "<b>Что это?</b>\n"
        "Приложение для анализа и прогноза цен криптовалют на основе "
        "нейронной сети LSTM.\n\n"
        "<b>Возможности:</b>\n"
        "• 📈 Прогноз цен на 1-7 дней\n"
        "• 🧠 Анализ 90 дней истории цен\n"
        "• 📊 Технический анализ\n"
        "• 📉 Интерактивные графики\n"
        "• 🎯 Торговые сигналы\n"
        "• 💳 Система подписок\n\n"
        "<b>Версия:</b> 2.0.0"
    )

    await callback.message.answer(about_text, parse_mode="HTML")

    logger.info(f"✅ Пользователь {callback.from_user.id} нажал кнопку 'О приложении'")


@router.message()
async def echo_handler(message: Message) -> None:
    """Обработчик для всех остальных сообщений"""

    response = (
        "👋 Привет! Я не понимаю эту команду.\n\n"
        "Введите /help для справки или нажмите кнопку ниже:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )],
        [InlineKeyboardButton(
            text="ℹ️ Справка",
            callback_data="help"
        )]
    ])

    await message.answer(response, reply_markup=keyboard)
    logger.info(f"ℹ️ Пользователь {message.from_user.id} отправил неизвестную команду: {message.text}")