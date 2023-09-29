import unittest
import os
import asyncio
from dotenv import load_dotenv
import telegram.ext
from telegram_task.line import LineManager, TaskException, JobOrder
from telegram_task.president import President
from telegram_task.samples import (
    SleepyWorker,
    MathematicalOperation,
    CalculatorJobDescription,
    CalculatorWorker
)

load_dotenv()

PROXY_URL = os.getenv('PROXY_URL')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TestEnterprise(unittest.IsolatedAsyncioTestCase):
    """Test the whole package, a president looking over one or more lines"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def test_president_telegram_bot(self):
        """Test succesful initiation of president and its telegram bot"""
        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        async with President(
            telegram_bot=application.bot, telegram_admin_id=TELEGRAM_CHAT_ID
        ) as president:
            await president.telegram_bot.get_me()
            await asyncio.sleep(3)
