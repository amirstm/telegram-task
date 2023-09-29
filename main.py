import os
import asyncio
import logging
import time
import threading
from dotenv import load_dotenv
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

    logger.addHandler(stream_handler)

    lm = telegram_task.line.LineManager(
        worker=telegram_task.samples.SleepyWorker()
    )
    print(lm.display_name)

    application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    president = President(
        telegram_bot=application.bot, telegram_admin_id=TELEGRAM_CHAT_ID
    )
    listener_thread = threading.Thread(
        target=kill_president,
        args=(president,)
    )
    listener_thread.start()
    president.start_operation()


if __name__ == '__main__':
    main()
