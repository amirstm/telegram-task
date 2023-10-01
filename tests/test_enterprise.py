import unittest
import os
import asyncio
from datetime import datetime, time
from dotenv import load_dotenv
import telegram.ext
from telegram_task.line import (
    LineManager,
    JobDescription,
    JobOrder,
    CronJobOrder
)
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

    async def test_president_telegram_bot_get_me(self):
        """Test succesful initiation of president and its telegram bot"""
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application, telegram_admin_id=TELEGRAM_CHAT_ID
        )
        bot_info = await president._telegram_app.bot.get_me()
        self.assertTrue(bot_info.id)

    def test_president_add_lines(self):
        """Test a president overseeing the operation of a sleepy worker"""
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
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

    def test_president_operation_synchronous(self):
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        president.start_operation(lifespan=1)

    async def run_job(self, president: President, line_manager: LineManager, job_description: JobDescription) -> bool:
        return await line_manager.perform_task(
            job_order=JobOrder(job_description=job_description),
            president=president
        )

    async def test_president_perform_single_job(self):
        """Test a president overseeing the operation of a sleepy worker"""
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
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
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
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

    def test_president_cron_job_init(self):
        """Test initiation of cron jobs on president"""
        if datetime.now().time() > time(hour=23, minute=58):
            return
        line_manager1 = LineManager(
            worker=SleepyWorker(),
            cron_job_orders=[
                CronJobOrder(time(hour=23, minute=59, second=59))
            ]
        )
        line_manager2 = LineManager(
            worker=CalculatorWorker(),
            cron_job_orders=[
                CronJobOrder(
                    time(hour=23, minute=59, second=58),
                    job_description=CalculatorJobDescription(
                        input1=2,
                        input2=3,
                        operation=MathematicalOperation.SUM
                    )
                ),
                CronJobOrder(
                    time(hour=23, minute=59, second=57),
                    job_description=CalculatorJobDescription(
                        input1=2,
                        input2=3,
                        operation=MathematicalOperation.MUL
                    )
                )]
        )
        president = President()
        president.add_line(line_manager1, line_manager2)
        tasks = president.get_daily_cron_jobs()
        self.assertTrue(len(tasks) == 3)
        self.assertTrue(tasks[0][1].daily_run_time.second == 57)
        self.assertTrue(tasks[1][1].daily_run_time.second == 58)
        self.assertTrue(tasks[2][1].daily_run_time.second == 59)

    async def test_president_process_cron_jobs(self):
        """Test processing of cron jobs on president"""
        if datetime.now().time() > time(hour=23, minute=58):
            return
        line_manager1 = LineManager(
            worker=SleepyWorker(),
            cron_job_orders=[
                CronJobOrder(time(hour=23, minute=59, second=59))
            ]
        )
        line_manager2 = LineManager(
            worker=CalculatorWorker(),
            cron_job_orders=[
                CronJobOrder(
                    time(hour=23, minute=59, second=58),
                    job_description=CalculatorJobDescription(
                        input1=2,
                        input2=3,
                        operation=MathematicalOperation.SUM
                    )
                ),
                CronJobOrder(
                    time(hour=23, minute=59, second=57),
                    job_description=CalculatorJobDescription(
                        input1=2,
                        input2=3,
                        operation=MathematicalOperation.MUL
                    )
                )]
        )
        application = telegram.ext.ApplicationBuilder().proxy_url(
            PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
        president = President(
            telegram_app=application,
            telegram_admin_id=TELEGRAM_CHAT_ID
        )
        president.add_line(line_manager1, line_manager2)
        await president.start_operation_async(lifespan=3)
        self.assertTrue(
            len([
                x
                for x in president.daily_cron_jobs
                if x[2] is None
            ]) == 3
        )
