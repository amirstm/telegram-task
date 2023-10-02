"""
President module is used for managing the whole construction.
Each president looks over several line managers, each of which
manage workers and their tasks.
Telegram bot is managed by the president too.
"""
from __future__ import annotations
from typing import Callable, Awaitable
import logging
import asyncio
import threading
from time import sleep
from datetime import datetime, date, time
import pytz
import telegram
import telegram.ext
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
import telegram_task.line


class President:
    """
    Manager class handles the scheduled run of workers, 
    as well as unscheduled runs commanded by the user. 
    """
    _LOGGER: logging.Logger = logging.getLogger(__name__)
    _INITIATOR_MESSAGE: str = "."

    def __init__(
            self,
            telegram_app: telegram.ext.Application = None,
            telegram_admin_id: int = None
    ):
        self.__telegram_app = telegram_app
        self.__telegram_admin_id = int(telegram_admin_id)
        self.__telegram_que: asyncio.Queue[telegram.Update] = None
        self.__is_running: bool = False
        self._lines: list[telegram_task.line.LineManager] = []
        self.__operation_loop: asyncio.AbstractEventLoop = None
        self.daily_cron_jobs: list[
            tuple[
                telegram_task.line.LineManager,
                telegram_task.line.CronJobOrder,
                bool
            ]
        ] = []

    def __operation_group(self) -> Callable[[], Awaitable[bool]]:
        """Returns the group of tasks run on operation"""
        return asyncio.gather(
            self.__telegram_listener(),
            self.__handle_crons()
        )

    def start_operation(self, lifespan: int = 0) -> None:
        """Start the operation of the enterprise after full initiation"""
        self._LOGGER.info("President is starting the operation.")
        self.__is_running = True
        self.__operation_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__operation_loop)
        if lifespan > 0:
            __killer_thread = threading.Thread(
                target=self.__automatic_killer, args=(lifespan,)
            )
            __killer_thread.start()
        try:
            self.__operation_loop.run_until_complete(self.__init_updater())
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
            await self.__init_updater()
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
        if self.__telegram_app:
            self._LOGGER.info("Initiating telegram bot.")
            self.__telegram_que = asyncio.Queue()
            __updater = telegram.ext.Updater(
                self.__telegram_app.bot,
                update_queue=self.__telegram_que
            )
            await __updater.initialize()
            await __updater.start_polling()
            await self.__telegram_app.job_queue.start()
            self._LOGGER.info("Telegram bot is initiated.")

    async def __telegram_listener(self) -> None:
        """Waiting for updates from telegram"""
        if self.__telegram_app:
            self._LOGGER.info("telegram_listener loop has started.")
            start_time_utc = datetime.now(tz=pytz.utc)
            while self.__is_running:
                update = await self.__telegram_que.get()
                self._LOGGER.info("Update from telegram %s", update)
                if self.__is_update_valid(update):
                    try:
                        if update.callback_query:
                            self.__handle_telegram_callback(update)
                        elif update.message and update.message.date > start_time_utc:
                            self.__handle_telegram_message(update)
                    except Exception as ex:
                        self._LOGGER.fatal(
                            "Exception on handling [%s]: %s",
                            str(update),
                            ex,
                            exc_info=True
                        )
                elif update.message.chat.type == telegram.constants.ChatType.PRIVATE:
                    self.__handle_message_from_unknown(update)
            self._LOGGER.info("telegram_listener is done.")

    def __handle_message_from_unknown(self, update: telegram.Update) -> None:
        """Handles a message received from an unknown user"""
        self.telegram_report(
            text=f"""
⚠️ Alert ⚠️
Message from unknown user [{update.effective_user.id}, \
{update.effective_user.full_name}, @{update.effective_user.username}]
"""
        )
        self.__telegram_app.job_queue.run_once(
            lambda context: context.bot.forward_message(
                chat_id=self.__telegram_admin_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            ),
            when=0
        )

    def __handle_telegram_message(self, update: telegram.Update) -> None:
        """Handle message from telegram admin"""
        if update.message.text == self._INITIATOR_MESSAGE:
            self.__telegram_introduction_message(update)

    def __handle_telegram_callback(self, update: telegram.Update) -> None:
        """Handle callback query from telegram admin"""
        callback_data_splitted = update.callback_query.data.split(",")
        match callback_data_splitted[0]:
            case "HighFive":
                self.__telegram_high_five(update=update)
            case "DailyTaskReport":
                self.__report_daily_tasks(do_log=False)
            case "NewJobPanel":
                self.__telegram_new_job_panel()
            case "SpecificNewJobPanel":
                self.__telegram_specific_new_job_panel(
                    callback_data=callback_data_splitted
                )

    def __telegram_specific_new_job_panel(
            self,
            callback_data: list[str]
    ) -> None:
        """
        Sends the panel for a specific job 
        so that the user proceeds with the new job request
        """
        job_name = callback_data[1]
        line = next(
            x
            for x in self._lines
            if x.display_name == job_name
        )
        job_order = telegram_task.line.JobOrder(
            job_description=line.worker.default_job_description()
        )

    def __telegram_new_job_panel(self) -> None:
        """Sends the panel so that the user chooses a new job"""
        text = "Please choose a job 🦾\n" + "\n".join(
            [
                f"{i+1}. <b>{x}</b>"
                for i, x in enumerate(self._lines)
            ]
        )
        reply_markup_buttons = [
            [
                InlineKeyboardButton(
                    text=str(i * 5 + j + 1),
                    callback_data=f"SpecificNewJobPanel,{x.display_name}"
                )
                for j, x in enumerate(self._lines[i:i + 5])
            ]
            for i in range(0, len(self._lines), 5)
        ]
        self.__telegram_app.job_queue.run_once(
            lambda context: context.bot.send_message(
                chat_id=self.__telegram_admin_id,
                text=text,
                parse_mode=telegram.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(reply_markup_buttons)
            ),
            when=0
        )

    def __telegram_high_five(self, update: telegram.Update) -> None:
        """Test method, high five on request"""
        self.__telegram_app.job_queue.run_once(
            lambda context: context.bot.answer_callback_query(
                callback_query_id=update.callback_query.id,
                text="One is glad to be of service 🙂 🙏",
                show_alert=True
            ),
            when=0
        )

    def __telegram_introduction_message(self, update: telegram.Update) -> None:
        self.__telegram_app.job_queue.run_once(
            lambda context: context.bot.send_message(
                chat_id=self.__telegram_admin_id,
                text=f"""
Hello <b>{update.effective_user.first_name}</b> 🙂
How may I help you today?
""",
                parse_mode=telegram.constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="High Five 🙏",
                                callback_data="HighFive"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Daily Task Report 📑",
                                callback_data="DailyTaskReport"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Got a Job? 🦾",
                                callback_data="NewJobPanel"
                            )
                        ]
                    ]
                )
            ),
            when=0
        )

    def __is_update_valid(self, update: telegram.Update) -> bool:
        """Checks if update is from the admin chat"""
        return update.effective_chat and \
            int(update.effective_chat.id) == self.__telegram_admin_id

    async def __handle_crons(self) -> None:
        """Handling cron jobs associated with lines"""
        self._LOGGER.info("Handling cron jobs has started.")
        while self.__is_running:
            today = date.today()
            self.daily_cron_jobs = self.get_daily_cron_jobs()
            self._LOGGER.info(
                "Handling [%d] cron jobs for [%s]",
                len(self.daily_cron_jobs),
                today
            )
            self.__report_daily_tasks(do_log=True)
            daily_tasks = [
                self.__convert_cron_job_to_task(job=x)
                for x in self.daily_cron_jobs
            ]
            await asyncio.gather(*daily_tasks)
            self._LOGGER.info(
                "Cron jobs for [%s] are complete",
                today
            )
            await asyncio.sleep(
                (
                    datetime.combine(datetime.now(), time.max) -
                    datetime.now()
                ).total_seconds())
        self._LOGGER.info("Handling cron jobs has been stopped.")

    async def __convert_cron_job_to_task(
            self,
            job: tuple[
                telegram_task.line.LineManager,
                telegram_task.line.CronJobOrder,
                bool
            ]
    ) -> None:
        """Convert cron jobs to awaitable tasks"""
        time_to_sleep = (
            datetime.combine(datetime.today(), job[1].daily_run_time) -
            datetime.now()
        ).total_seconds()
        if time_to_sleep > 0:
            await asyncio.sleep(time_to_sleep)
        job[2] = await job[0].perform_task(job_order=job[1], president=self)

    def __report_daily_tasks(
            self,
            do_log: bool
    ) -> None:
        """Report daily tasks on telegram"""
        def job_status_to_emoji(status: bool) -> str:
            match status:
                case True:
                    return "✅"
                case False:
                    return "❌"
                case _:
                    return "⚙️"
        report = f"📑 Cron jobs for {datetime.now():%Y/%m/%d}:\n" + \
            "\n".join(
                [
                    f"{job_status_to_emoji(x[2])} {x[0]} 🕔 {x[1].daily_run_time:%H:%M:%S}"
                    for x in self.daily_cron_jobs
                ]
            ) \
            if self.daily_cron_jobs \
            else f"📑 No cron jobs for {datetime.now():%Y/%m/%d}."
        if do_log:
            self._LOGGER.info(report)
        self.telegram_report(report)

    def get_daily_cron_jobs(
            self
    ) -> list[tuple[
        telegram_task.line.LineManager,
        telegram_task.line.CronJobOrder,
        bool
    ]]:
        """Get cron tasks for the rest of the day"""
        now_datetime = datetime.now()
        now_time = now_datetime.time()
        weekday = now_datetime.weekday()
        return sorted([
            [x, y, None] for x in self._lines
            for y in x.cron_job_orders
            if weekday not in y.off_days and y.daily_run_time > now_time
        ], key=lambda x: x[1].daily_run_time)

    def add_line(self, *args: telegram_task.line.LineManager) -> None:
        """Add new line managers to the enterprise"""
        self._lines.extend(args)

    def telegram_report(self, text: str) -> None:
        """Telegram simple report making"""
        if self.__telegram_app:
            self.__telegram_app.job_queue.run_once(
                lambda context: context.bot.send_message(
                    chat_id=self.__telegram_admin_id,
                    text=text,
                    parse_mode=telegram.constants.ParseMode.HTML
                ),
                when=0
            )
