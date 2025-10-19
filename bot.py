import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database.db import migrate
from handlers import start, protection_add, protection_view, admin_panel
from utils.scheduler import setup_scheduler
from utils.articles import seed_articles
from pathlib import Path

logging.basicConfig(level=logging.INFO)


def load_env():
    # Явно указываем путь к .env в корне проекта
    env_path = Path(__file__).parent / ".env"
    print(f"Loading .env from: {env_path}")
    load_dotenv(dotenv_path=env_path, override=True)

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set or .env not found")
    return token


async def main():
    token = load_env()

    # ✅ Новый блок — загрузка и вывод ADMIN_IDS
    ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")
    print("ADMIN_IDS =", ADMIN_IDS)

    migrate()

    # Сид артикулов (пример)
    seed_articles([
        ("8001", "замок"),
        ("8001", "клей"),
        ("8002", "замок"),
        ("8002", "клей"),
        ("9001", "замок"),
        ("9002", "клей"),
    ])

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    # Роутеры
    dp.include_routers(
        start.router,
        protection_add.router,
        protection_view.router,
        admin_panel.router
    )

    # ✅ Передаём список админов в контекст диспетчера
    dp["ADMIN_IDS"] = ADMIN_IDS

    # Планировщик авто-закрытий
    setup_scheduler()

    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот успешно запущен и готов к работе.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
