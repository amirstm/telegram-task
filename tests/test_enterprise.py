import unittest
import os
import asyncio
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
        bot_info = await president.telegram_app.bot.get_me()
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

    async def test_president_perform_single_job(self):
        """Test a president overseeing the operation of a sleepy worker"""
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

    async def run_jobs(self, president: President, jobs: list[(LineManager, JobDescription)]) -> list[bool]:
        results = []
        for line_manager, job_description in jobs:
            result = await line_manager.perform_task(
                job_order=JobOrder(job_description=job_description),
                president=president
            )
            await asyncio.sleep(2)
            results.append(result)
        return results

    async def test_president_perform_multiple_jobs(self):
        """Test a president overseeing the operation of a multiple lines"""
        application = telegram.ext.ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        line_manager1 = LineManager(worker=SleepyWorker())
        line_manager2 = LineManager(worker=CalculatorWorker())
        president.add_line(
            line_manager1,
            line_manager2
        )
        group = asyncio.gather(
            president.start_operation_async(lifespan=10),
            self.run_jobs(
                president=president,
                jobs=[
                    (line_manager1, JobDescription()),
                    (line_manager2, CalculatorJobDescription(
                        input1=2, input2=3, operation=MathematicalOperation.SUM
                    )),
                    (line_manager2, CalculatorJobDescription(
                        input1=2, input2=3, operation=MathematicalOperation.POW
                    )),
                    (line_manager2, CalculatorJobDescription(
                        input1=2, input2=0, operation=MathematicalOperation.DIV
                    ))
                ]
            )
        )
        _, successes = await group
        self.assertTrue(successes[0] and successes[1])
        self.assertFalse(successes[2] or successes[3])
