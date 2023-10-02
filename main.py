import os
import logging
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
from logging.handlers import TimedRotatingFileHandler
import telegram.ext
from telegram_task.president import President
from telegram_task.line import (
    LineManager,
    CronJobOrder,
)
from telegram_task.samples import (
    SleepyWorker,
    CalculatorJobDescription,
    CalculatorWorker,
    MathematicalOperation
)
from dataclasses import dataclass

load_dotenv()

PROXY_URL = os.getenv('PROXY_URL')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def main():
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

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    application = telegram.ext.ApplicationBuilder().proxy_url(
        PROXY_URL).token(TELEGRAM_BOT_TOKEN).build()
    president = President(
        telegram_app=application,
        telegram_admin_id=TELEGRAM_CHAT_ID
    )
    line_manager1 = LineManager(
        worker=SleepyWorker(),
        cron_job_orders=[
            CronJobOrder((datetime.now() + timedelta(seconds=300)).time())
        ]
    )
    line_manager2 = LineManager(
        worker=CalculatorWorker(),
        cron_job_orders=[
            CronJobOrder(
                daily_run_time=(
                    datetime.now() + timedelta(seconds=600)
                ).time(),
                job_description=CalculatorJobDescription(
                    input1=2,
                    input2=3,
                    operation=MathematicalOperation.POW
                )
            ),
            CronJobOrder(
                daily_run_time=time(hour=23, minute=59, second=57),
                job_description=CalculatorJobDescription(
                    input1=2,
                    input2=3,
                    operation=MathematicalOperation.MUL
                )
            )]
    )
    president.add_line(line_manager1, line_manager2)
    president.start_operation()


if __name__ == '__main__':
    main()
