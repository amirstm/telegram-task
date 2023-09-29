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

    @classmethod
    async def create(
        cls,
        telegram_bot: telegram.Bot = None,
        telegram_admin_id: int = None
    ):
        """Class method for creating an instance asynchronously"""
        self = President(telegram_bot=telegram_bot,
                         telegram_admin_id=telegram_admin_id)
        await self.__init_updater()
        return self

    def __init__(
            self,
            telegram_bot: telegram.Bot = None,
            telegram_admin_id: int = None
    ):
        self.telegram_bot = telegram_bot
        self.telegram_admin_id = telegram_admin_id
        self.__telegram_que: asyncio.Queue = None
        self.__updater: telegram.ext.Updater = None
        self._lines: list[telegram_task.line.LineManager] = []

    async def __aenter__(self):
        await self.__init_updater()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.__close_updater()

    async def __init_updater(self):
        """Initiates the telegram updater and starts polling"""
        if self.telegram_bot:
            self._LOGGER.info("Initiating telegram bot listener.")
            self.__telegram_que = asyncio.Queue()
            self.__updater = telegram.ext.Updater(
                self.telegram_bot, update_queue=self.__telegram_que)
            await self.__updater.initialize()
            await self.__updater.start_polling()
            self._LOGGER.info("Telegram bot has started listening.")

    async def __close_updater(self):
        """Close the telegram updater"""
        if self.telegram_bot:
            await self.__updater.stop()
            self._LOGGER.info("Terminating telegram bot listener.")

    def add_line(self, *args: telegram_task.line.LineManager):
        """Add new line managers to the enterprise"""
        self._lines.extend(args)
