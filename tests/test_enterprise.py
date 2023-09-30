import unittest
import os
import threading
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import telegram.ext
from telegram_task.line import LineManager, JobDescription, JobOrder
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
            telegram_app=application, telegram_admin_id=TELEGRAM_CHAT_ID
        )
        bot_info = await president.telegram_bot.get_me()
        self.assertTrue(bot_info.id)

    def test_president_add_lines(self):
        """Test a president overseeing the operation of a sleepy worker"""
        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        president.add_line(
            LineManager(worker=SleepyWorker()),
            LineManager(worker=CalculatorWorker()),
        )
        print(president._lines)
        self.assertTrue(
            any((
                x for x in president._lines if isinstance(x.worker, SleepyWorker) and x.display_name == SleepyWorker.__name__
            )))
        self.assertTrue(
            any((
                x for x in president._lines if isinstance(x.worker, CalculatorWorker) and x.display_name == CalculatorWorker.__name__
            )))

    async def run_job(self, president: President, line_manager: LineManager, job_description: JobDescription) -> bool:
        return await line_manager.perform_task(
            job_order=JobOrder(job_description=job_description),
            president=president
        )

    def test_president_operation_synchronous(self):
        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        line_manager = LineManager(worker=SleepyWorker())
        president.add_line(
            line_manager,
        )
        president.start_operation(lifespan=1)

    async def test_president_perform_jobs_outside_operations(self):
        """Test a president overseeing the operation of a sleepy worker"""
        logger = logging.getLogger("telegram_task")

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

        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        line_manager = LineManager(worker=SleepyWorker())
        president.add_line(
            line_manager,
        )
        group = asyncio.gather(
            president.start_operation_async(lifespan=5),
            self.run_job(
                president=president,
                line_manager=line_manager,
                job_description=JobDescription()
            )
        )
        _, success = await group
        self.assertTrue(success)

    # def test_president_perform_jobs_realtime(self):
    #     """Test a president overseeing the operation of a sleepy worker"""
    #     application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    #     president = President(
    #         telegram_bot=application.bot,
    #         telegram_admin_id=TELEGRAM_CHAT_ID
    #     )
    #     line_manager = LineManager(worker=SleepyWorker())
    #     president.add_line(
    #         line_manager,
    #     )

    #     listener_thread = threading.Thread(
    #         target=self.run_job,
    #         args=(line_manager,)
    #     )
    #     listener_thread.start()
    #     president.start_operation()
