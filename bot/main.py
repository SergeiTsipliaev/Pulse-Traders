import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo

from config import BOT_TOKEN, WEB_APP_URL
from bot.handlers import router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Установка команд в меню"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="ℹ️ Справка"),
        BotCommand(command="about", description="📱 О приложении"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    logger.info("✅ Команды установлены")


async def set_menu_button(bot: Bot):
    """Установка Menu Button"""
    if not WEB_APP_URL:
        logger.warning("⚠️  WEB_APP_URL не установлен")
        return
    
    menu_button = MenuButtonWebApp(
        text="📱 Открыть приложение",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    await bot.set_chat_menu_button(menu_button=menu_button)
    logger.info(f"✅ Menu Button установлен: {WEB_APP_URL}")


async def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return
    
    logger.info("🤖 Запуск Telegram бота...")
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот: @{me.username} (ID: {me.id})")
        
        await set_bot_commands(bot)
        await set_menu_button(bot)
        
        logger.info("🎯 Polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())