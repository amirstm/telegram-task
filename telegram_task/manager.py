import logging
import telegram
import asyncio
import time


class Manager:
    """
    Manager class handles the scheduled run of workers, 
    as well as unscheduled runs commanded by the user. 
    """
    _LOGGER = logging.getLogger(__name__)

    @classmethod
    async def create(cls, telegram_bot: telegram.Bot = None):
        """Class method for creating an instance asynchronously"""
        self = Manager(telegram_bot=telegram_bot)
        await self.__init_updater()
        return self

    def __init__(
            self,
            telegram_bot: telegram.Bot = None,
    ):
        self._telegram_bot = telegram_bot

    async def __aenter__(self):
        await self.__init_updater()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.__close_updater()

    async def __init_updater(self):
        """Initiates the telegram updater and starts polling"""
        if self._telegram_bot:
            self._LOGGER.info("Initiating telegram bot listener.")
            self.__telegram_que: asyncio.Queue = asyncio.Queue()
            self.__updater: telegram.ext.Updater = telegram.ext.Updater(
                self._telegram_bot, update_queue=self.__telegram_que)
            await self.__updater.initialize()
            await self.__updater.start_polling()
            self._LOGGER.info("Telegram bot has started listening.")

    async def __close_updater(self):
        """Close the telegram updater"""
        if self._telegram_bot:
            await self.__updater.stop()
            self._LOGGER.info("Terminating telegram bot listener.")
