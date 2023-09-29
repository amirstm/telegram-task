import unittest
import os
import asyncio
from dotenv import load_dotenv
import telegram.ext
from telegram_task.line import LineManager
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
        president = President(
            telegram_bot=application.bot, telegram_admin_id=TELEGRAM_CHAT_ID
        )
        bot_info = await president.telegram_bot.get_me()
        self.assertTrue(bot_info.id)

    async def test_president_with_sleepy_worker(self):
        """Test a president overseeing the operation of a sleepy worker"""
        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_bot=application.bot,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        president.add_line(
            LineManager(worker=SleepyWorker()),
            LineManager(worker=CalculatorWorker()),
        )
        print(president._lines)
        self.assertTrue(
            any((
                x for x in president._lines if isinstance(x.worker, SleepyWorker)
            )))
        self.assertTrue(
            any((
                x for x in president._lines if isinstance(x.worker, CalculatorWorker)
            )))
