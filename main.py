import os
import asyncio
import logging
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Updater, CallbackContext, ExtBot, Application
import telegram.ext
from telegram_task import manager
from dataclasses import dataclass

load_dotenv()

PROXY_URL = os.getenv('PROXY_URL')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def main():
    logger = logging.getLogger(None)  # "telegram_task.manager")
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s: %(message)s')
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)

    application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    # manager_ins = await manager.Manager.create(application.bot)

    async with manager.Manager(application.bot) as manager_ins:
        await asyncio.sleep(10)
    # Option 1
    # update = await que.get()

    # Option 2, replace option 1 if you like
    # update = que.get_nowait()


if __name__ == '__main__':
    asyncio.run(main())
