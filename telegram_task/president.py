"""
President module is used for managing the whole construction.
Each president looks over several line managers, each of which
manage workers and their tasks.
Telegram bot is managed by the president too.
"""
from __future__ import annotations
from typing import Callable, Awaitable, get_type_hints
from enum import Enum
import logging
import uuid
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


class TelegramDeputy:
    """
    Takes over all the president's tasks 
    that are related to telegram
    """
    _LOGGER: logging.Logger = logging.getLogger(__name__)
    _INITIATOR_MESSAGE: str = "."

    def __init__(
            self,
            telegram_app: telegram.ext.Application = None,
            telegram_admin_id: int = None,
    ):
        self.president: President = None
        self.__telegram_app: telegram.ext.Application = telegram_app
        self.__telegram_admin_id: int = int(
            telegram_admin_id
        ) if telegram_admin_id else None
        self.__telegram_que: asyncio.Queue[telegram.Update] = None
        self.__telegram_bot_username: str = None
        self.__new_job_panels: list[
            tuple[
                telegram_task.line.LineManager,
                telegram_task.line.JobOrder,
                telegram.Message
            ]] = []

    async def init_updater(self) -> None:
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

    async def telegram_listener(self) -> None:
        """Waiting for updates from telegram"""
        if self.__telegram_app:
            self._LOGGER.info("telegram_listener loop has started.")
            start_time_utc = datetime.now(tz=pytz.utc)
            while self.president.is_running:
                update = await self.__telegram_que.get()
                self._LOGGER.info("Update from telegram %s", update)
                if self.__is_update_valid(update):
                    try:
                        if update.callback_query:
                            await self.__handle_telegram_callback_query(update)
                        elif update.message and update.message.date > start_time_utc:
                            await self.__handle_telegram_message(update)
                    except ValueError:
                        self._LOGGER.error(
                            "ValueError: exception on converting input."
                        )
                    except KeyError:
                        self._LOGGER.error(
                            "KeyError: exception on converting input."
                        )
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

    async def __handle_telegram_message(self, update: telegram.Update) -> None:
        """Handle message from telegram admin"""
        message_splitted = update.message.text.split(" ")
        match message_splitted[0]:
            case self._INITIATOR_MESSAGE:
                self.__telegram_introduction_message(update)
            case _:
                if message_splitted[0] == "@" + await self.__get_telegram_bot_username():
                    await self.__handle_telegram_inline_query(message_splitted)

    async def __handle_telegram_inline_query(self, message_splitted: list[str]) -> None:
        """Handle inline query from telegram admin"""
        if len(message_splitted) > 1:
            match message_splitted[1]:
                case "SpecificNewJobPanelUpdate":
                    await self.__telegram_specific_new_job_panel_update(
                        message_splitted=message_splitted
                    )

    async def __handle_telegram_callback_query(self, update: telegram.Update) -> None:
        """Handle callback query from telegram admin"""
        callback_data_splitted = update.callback_query.data.split(",")
        match callback_data_splitted[0]:
            case "HighFive":
                self.__telegram_high_five(update=update)
            case "DailyTaskReport":
                self.report_daily_tasks(do_log=False)
            case "NewJobPanel":
                self.__telegram_new_job_panel()
            case "SpecificNewJobPanel":
                await self.__telegram_specific_new_job_panel(
                    callback_data=callback_data_splitted
                )
            case "ExecuteSpecificNewJob":
                await self.__telegram_execute_specific_new_job(
                    callback_data=callback_data_splitted
                )

    async def __telegram_execute_specific_new_job(
            self,
            callback_data: list[str]
    ) -> None:
        """Executes the new job from its specifications"""
        if len(callback_data) > 1:
            job_code = uuid.UUID(callback_data[1])
            print(job_code)
            job_panel = next(
                x
                for x in self.__new_job_panels
                if x[1].job_code == job_code
            )
            text, _ = self.__telegram_specific_new_job_panel_message(
                line_manager=job_panel[0],
                job_order=job_panel[1]
            )
            await self.__telegram_app.bot.edit_message_text(
                chat_id=self.__telegram_admin_id,
                message_id=job_panel[2].id,
                text=f"{text}\n\nRoger that 🦾✅",
                parse_mode=telegram.constants.ParseMode.HTML,
            )
            self.__new_job_panels.remove(job_panel)
            asyncio.create_task(
                job_panel[0].perform_task(
                    job_order=job_panel[1],
                    president=self.president
                ))

    async def __telegram_specific_new_job_panel_update(self, message_splitted: list[str]) -> None:
        """Updates some parameter in the new job panel"""
        if len(message_splitted) > 7:
            property_name = message_splitted[2]
            job_code = uuid.UUID(hex=message_splitted[5])
            new_value_str = message_splitted[7]
            job_panel = next(
                x
                for x in self.__new_job_panels
                if x[1].job_code == job_code
            )
            property_type = get_type_hints(
                job_panel[1].job_description
            )[property_name]
            job_panel[1].job_description.__dict__[
                property_name
            ] = self.__convert_str_to_type(
                raw_val=new_value_str,
                to_type=property_type
            )
            text, inline_keyboard = self.__telegram_specific_new_job_panel_message(
                line_manager=job_panel[0],
                job_order=job_panel[1]
            )
            message = await self.__telegram_app.bot.edit_message_text(
                chat_id=self.__telegram_admin_id,
                message_id=job_panel[2].id,
                text=text,
                parse_mode=telegram.constants.ParseMode.HTML,
                reply_markup=inline_keyboard
            )
            self.__new_job_panels.remove(job_panel)
            self.__new_job_panels.append((
                job_panel[0],
                job_panel[1],
                message
            ))

    def __convert_str_to_type(self, raw_val: str, to_type: type) -> type.__name__:
        """Converts string to the given type"""
        if to_type in [int, float, str]:
            return to_type(raw_val)
        if to_type == bool:
            return raw_val.lower() in ["true", "1", "y"]
        if issubclass(to_type, Enum):
            return to_type[raw_val]
        raise ValueError

    async def __telegram_specific_new_job_panel(
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
            for x in self.president.lines
            if x.display_name == job_name
        )
        job_order = telegram_task.line.JobOrder(
            job_description=line.worker.default_job_description()
        )
        text, inline_keyboard = self.__telegram_specific_new_job_panel_message(
            line_manager=line,
            job_order=job_order
        )
        message = await self.__telegram_app.bot.send_message(
            chat_id=self.__telegram_admin_id,
            text=text,
            parse_mode=telegram.constants.ParseMode.HTML,
            reply_markup=inline_keyboard
        )
        self.__new_job_panels.append((line, job_order, message))

    def __telegram_specific_new_job_panel_message(
            self,
            line_manager: telegram_task.line.LineManager,
            job_order: telegram_task.line.JobOrder
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Returns the message text and keyboard for a specific job request"""
        type_hints = get_type_hints(
            job_order.job_description,
            include_extras=False
        ) if job_order.job_description.__dict__ else {}
        text = f"""
Please validate the job description for <b>{line_manager}</b> \
📝 with code <b>{job_order.job_code}</b> 🔑

""" + "\n".join(
            [
                f"<b>{key}</b> ({type_hints[key].__name__}) ➡️  {val}"
                for key, val in job_order.job_description.__dict__.items()
            ]
        )
        keybord_rows = [
            [
                InlineKeyboardButton(
                    text=f"{key} ✏️",
                    switch_inline_query_current_chat=f"SpecificNewJobPanelUpdate {key} "
                    + f"on job {job_order.job_code} : "
                )
            ]
            for key, val in job_order.job_description.__dict__.items()
        ]
        keybord_rows.append(
            [
                InlineKeyboardButton(
                    text="Execute ✅",
                    callback_data=f"ExecuteSpecificNewJob,{job_order.job_code}"
                )
            ]
        )
        return text, InlineKeyboardMarkup(keybord_rows)

    def __telegram_new_job_panel(self) -> None:
        """Sends the panel so that the user chooses a new job"""
        text = "Please choose a job 🦾\n" + "\n".join(
            [
                f"{i+1}. <b>{x}</b>"
                for i, x in enumerate(self.president.lines)
            ]
        )
        reply_markup_buttons = [
            [
                InlineKeyboardButton(
                    text=str(i * 5 + j + 1),
                    callback_data=f"SpecificNewJobPanel,{x.display_name}"
                )
                for j, x in enumerate(self.president.lines[i:i + 5])
            ]
            for i in range(0, len(self.president.lines), 5)
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

    async def __get_telegram_bot_username(self) -> str:
        """Returns the telegram bot username, either from memory or by fetching"""
        if self.__telegram_bot_username:
            return self.__telegram_bot_username
        self.__telegram_bot_username = (await
                                        self.__telegram_app.bot.get_me()
                                        ).username
        return self.__telegram_bot_username

    def __is_update_valid(self, update: telegram.Update) -> bool:
        """Checks if update is from the admin chat"""
        return update.effective_chat and \
            int(update.effective_chat.id) == self.__telegram_admin_id

    def report_daily_tasks(
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
                    for x in self.president.daily_cron_jobs
                ]
            ) \
            if self.president.daily_cron_jobs \
            else f"📑 No cron jobs for {datetime.now():%Y/%m/%d}."
        if do_log:
            self._LOGGER.info(report)
        self.telegram_report(report)


class President:
    """
    President class handles the scheduled run of workers, 
    as well as unscheduled runs commanded by the user. 
    """
    _LOGGER: logging.Logger = logging.getLogger(__name__)

    def __init__(
            self,
            telegram_deputy: TelegramDeputy = None
    ):
        self.__telegram_deputy: TelegramDeputy = telegram_deputy
        if self.__telegram_deputy:
            self.__telegram_deputy.president = self
        self.is_running: bool = False
        self.lines: list[telegram_task.line.LineManager] = []
        self.__operation_loop: asyncio.AbstractEventLoop = None
        self.daily_cron_jobs: list[
            tuple[
                telegram_task.line.LineManager,
                telegram_task.line.CronJobOrder,
                bool
            ]] = []

    def __operation_group(self) -> Callable[[], Awaitable[bool]]:
        """Returns the group of tasks run on operation"""
        return asyncio.gather(
            self.__telegram_deputy.telegram_listener(),
            self.__handle_crons()
        )

    def start_operation(self, lifespan: int = 0) -> None:
        """Start the operation of the enterprise after full initiation"""
        self._LOGGER.info("President is starting the operation.")
        self.is_running = True
        self.__operation_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__operation_loop)
        if lifespan > 0:
            __killer_thread = threading.Thread(
                target=self.__automatic_killer, args=(lifespan,)
            )
            __killer_thread.start()
        try:
            self.__operation_loop.run_until_complete(
                self.__telegram_deputy.init_updater()
            )
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
        self.is_running = True
        try:
            await self.__telegram_deputy.init_updater()
            group = self.__operation_group()
            await asyncio.wait_for(group, timeout=lifespan)
        except asyncio.exceptions.TimeoutError:
            self.is_running = False
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
        self.is_running = False
        self.__operation_loop.stop()

    async def __handle_crons(self) -> None:
        """Handling cron jobs associated with lines"""
        self._LOGGER.info("Handling cron jobs has started.")
        while self.is_running:
            today = date.today()
            self.daily_cron_jobs = self.get_daily_cron_jobs()
            self._LOGGER.info(
                "Handling [%d] cron jobs for [%s]",
                len(self.daily_cron_jobs),
                today
            )
            self.__telegram_deputy.report_daily_tasks(do_log=True)
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
            [x, y, None] for x in self.lines
            for y in x.cron_job_orders
            if weekday not in y.off_days and y.daily_run_time > now_time
        ], key=lambda x: x[1].daily_run_time)

    def add_line(self, *args: telegram_task.line.LineManager) -> None:
        """Add new line managers to the enterprise"""
        self.lines.extend(args)

    def telegram_report(self, text: str) -> None:
        """Telegram simple report making"""
        if self.__telegram_deputy:
            self.__telegram_deputy.telegram_report(text=text)
