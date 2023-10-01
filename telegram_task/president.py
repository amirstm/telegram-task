"""
President module is used for managing the whole construction.
Each president looks over several line managers, each of which
manage workers and their tasks.
Telegram bot is managed by the president too.
"""
from __future__ import annotations
import logging
import asyncio
import threading
from time import sleep
from datetime import datetime, date
import telegram
import telegram.ext
import telegram_task.line


class President:
    """
    Manager class handles the scheduled run of workers, 
    as well as unscheduled runs commanded by the user. 
    """
    _LOGGER = logging.getLogger(__name__)

    def __init__(
            self,
            telegram_app: telegram.ext.Application = None,
            telegram_admin_id: int = None
    ):
        self._telegram_app = telegram_app
        self._telegram_admin_id = telegram_admin_id
        self.__telegram_que: asyncio.Queue = None
        self.__is_running: bool = False
        self._lines: list[telegram_task.line.LineManager] = []
        self.__operation_loop: asyncio.AbstractEventLoop = None
        self.__killer_thread: threading.Thread = None

    def __operation_group(self) -> asyncio.Future:
        """Returns the group of tasks run on operation"""
        return asyncio.gather(self.__init_updater())

    def start_operation(self, lifespan: int = 0) -> None:
        """Start the operation of the enterprise after full initiation"""
        self._LOGGER.info("President is starting the operation.")
        self.__is_running = True
        self.__operation_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__operation_loop)
        if lifespan > 0:
            self.__killer_thread = threading.Thread(
                target=self.__automatic_killer, args=(lifespan,)
            )
            self.__killer_thread.start()
        try:
            group = self.__operation_group()
            _ = self.__operation_loop.run_until_complete(group)
        except RuntimeError:
            self._LOGGER.info("Telegram bot listener is terminated.")
        except Exception as ex:
            self._LOGGER.error(ex, exc_info=True)
            self._LOGGER.info(
                "Telegram bot listener is terminated in an improper manner."
            )

    async def start_operation_async(self, lifespan: int = 0) -> None:
        """Start the operation of the enterprise after full initiation"""
        self._LOGGER.info(
            "President is starting the operation asynchronously."
        )
        self.__is_running = True
        try:
            group = self.__operation_group()
            await asyncio.wait_for(group, timeout=lifespan)
        except asyncio.exceptions.TimeoutError:
            self.__is_running = False
            self._LOGGER.info("Telegram bot listener is terminated.")
        except Exception as ex:
            self._LOGGER.error(ex, exc_info=True)
            self._LOGGER.info(
                "Telegram bot listener is terminated in an improper manner."
            )

    def __automatic_killer(self, lifespan) -> None:
        """Method used for setting an automatic lifespan for operation"""
        self._LOGGER.info(
            "Automatic killer is set to stop operation after %d seconds.",
            lifespan
        )
        sleep(lifespan)
        self._LOGGER.info("Automatic killer is killing the operation.")
        self.stop_operation()

    def stop_operation(self) -> None:
        """Stop the enterprise operation"""
        self._LOGGER.info("President is stopping the operation.")
        self.__is_running = False
        self.__operation_loop.stop()

    async def __init_updater(self) -> None:
        """Initiates the telegram updater and starts polling"""
        if self._telegram_app:
            self._LOGGER.info("Initiating telegram bot listener.")
            self.__telegram_que = asyncio.Queue()
            __updater = telegram.ext.Updater(
                self._telegram_app.bot, update_queue=self.__telegram_que
            )
            await __updater.initialize()
            await __updater.start_polling()
            await self._telegram_app.job_queue.start()
            self._LOGGER.info("Telegram bot has started listening.")
            await self.__telegram_listener()
            await __updater.stop()
            await self._telegram_app.job_queue.stop()
            self._LOGGER.info("Terminating telegram bot listener.")

    async def __telegram_listener(self) -> None:
        """Waiting for updates from telegram"""
        self._LOGGER.info("telegram_listener loop has started.")
        while self.__is_running:
            new_update = await self.__telegram_que.get()
            self._LOGGER.info("Update from telegram %s", new_update)
        self._LOGGER.info("telegram_listener is done.")

    async def __handle_crons(self) -> None:
        """Handling cron jobs associated with lines"""
        self._LOGGER.info("Handling cron jobs has started.")
        while self.__is_running:
            daily_tasks = self.get_daily_tasks()
            self._LOGGER.info(
                "Handling [%d] cron jobs for [%s]",
                len(daily_tasks),
                date.today()
            )
            self.__report_daily_tasks(daily_tasks)

    def __report_daily_tasks(
            self,
            daily_tasks: list[tuple[
                telegram_task.line.LineManager,
                telegram_task.line.CronJobOrder
            ]]
    ) -> None:
        """Report daily tasks on telegram"""
        report = f"📑 Cron jobs for {datetime.now():%Y/%m/%d}\n" + \
            "\n".join(
                [
                    f"⚙️ {x[0]} 🕔 {x[1].daily_run_time:%H:%M:%S}"
                    for x in daily_tasks
                ]
            ) \
            if daily_tasks \
            else f"📑 No cron jobs for {datetime.now():%Y/%m/%d}"
        self._LOGGER.info(report)
        self.telegram_report(report)

    def get_daily_tasks(
            self
    ) -> list[tuple[
        telegram_task.line.LineManager,
        telegram_task.line.CronJobOrder
    ]]:
        """Get cron task for the rest of the day"""
        now_datetime = datetime.now()
        now_time = now_datetime.time()
        weekday = now_datetime.weekday()
        return sorted([
            [x, y] for x in self._lines
            for y in x.cron_job_orders
            if weekday not in y.off_days and y.daily_run_time > now_time
        ], key=lambda x: x[1].daily_run_time)

    def add_line(self, *args: telegram_task.line.LineManager) -> None:
        """Add new line managers to the enterprise"""
        self._lines.extend(args)

    def telegram_report(self, text: str) -> None:
        """Telegram simple report making"""
        if self._telegram_app:
            self._telegram_app.job_queue.run_once(
                lambda context: context.bot.send_message(
                    chat_id=self._telegram_admin_id,
                    text=text,
                    parse_mode='html'
                ),
                when=0
            )
