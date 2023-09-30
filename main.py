import os
import asyncio
import logging
import time
import threading
from dotenv import load_dotenv
from logging.handlers import TimedRotatingFileHandler
import telegram.ext
from telegram_task.president import President
import telegram_task
from dataclasses import dataclass

load_dotenv()

PROXY_URL = os.getenv('PROXY_URL')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def kill_president(president):
    time.sleep(10)
    print("Killing president")
    president.stop_operation()


def main():
    logger = logging.getLogger(None)  # "telegram_task.manager")
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s: %(message)s')
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s: %(message)s')
    logger.setLevel(logging.INFO)
    logFilePath = "logs/log_"
    file_handler = TimedRotatingFileHandler(
        filename=logFilePath, when='midnight', backupCount=30)
    file_handler.suffix = '%Y_%m_%d.log'
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    president = President(
        telegram_app=application, telegram_admin_id=TELEGRAM_CHAT_ID
    )
    # listener_thread = threading.Thread(
    #     target=kill_president,
    #     args=(president,)
    # )
    # listener_thread.start()
    president.start_operation(lifespan=3)


if __name__ == '__main__':
    main()
