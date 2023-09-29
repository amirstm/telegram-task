"""
President module is used for managing the whole construction.
Each president looks over several line managers, each of which
manage workers and their tasks.
Telegram bot is managed by the president too.
"""
from __future__ import annotations
import logging
import asyncio
import telegram
import telegram_task.line


class President:
    """
    Manager class handles the scheduled run of workers, 
    as well as unscheduled runs commanded by the user. 
    """
    _LOGGER = logging.getLogger(__name__)

    def __init__(
            self,
            telegram_bot: telegram.Bot = None,
            telegram_admin_id: int = None
    ):
        self.telegram_bot = telegram_bot
        self.telegram_admin_id = telegram_admin_id
        self.__telegram_que: asyncio.Queue = None
        self.__updater: telegram.ext.Updater = None
        self.__is_listening: bool = False
        self._lines: list[telegram_task.line.LineManager] = []
        self.__operation_loop: asyncio.AbstractEventLoop = None

    def start_operation(self) -> None:
        """Start the operation of the enterprise after full initiation"""
        self.__operation_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__operation_loop)
        try:
            group = asyncio.gather(self.__init_updater())
            self.__operation_loop.run_until_complete(group)
        except RuntimeError:
            self._LOGGER.info("Telegram bot listener is terminated.")

    def stop_operation(self) -> None:
        """Stop the enterprise operation"""
        self.__is_listening = False
        self.__operation_loop.stop()

    async def __init_updater(self) -> None:
        """Initiates the telegram updater and starts polling"""
        if self.telegram_bot:
            self._LOGGER.info("Initiating telegram bot listener.")
            self.__is_listening = True
            self.__telegram_que = asyncio.Queue()
            self.__updater = telegram.ext.Updater(
                self.telegram_bot, update_queue=self.__telegram_que)
            await self.__updater.initialize()
            await self.__updater.start_polling()
            self._LOGGER.info("Telegram bot has started listening.")
            await self.__telegram_listener()
            await self.__updater.stop()
            self._LOGGER.info("Terminating telegram bot listener.")

    async def __telegram_listener(self) -> None:
        self._LOGGER.info("telegram_listener loop has started.")
        while self.__is_listening:
            new_update = await self.__telegram_que.get()
            self._LOGGER.info("Update from telegram %s", new_update)
        self._LOGGER.info("telegram_listener is done.")

    def add_line(self, *args: telegram_task.line.LineManager) -> None:
        """Add new line managers to the enterprise"""
        self._lines.extend(args)
