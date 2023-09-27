"""
President module is used for managing the whole construction.
Each president looks over several line managers, each of which
manage workers and their tasks.
Telegram bot is managed by the president too.
"""
import logging
import asyncio
import telegram


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
        self._telegram_bot = telegram_bot
        self._telegram_admin_id = telegram_admin_id
        self.__telegram_que: asyncio.Queue = None
        self.__updater: telegram.ext.Updater = None

    async def __aenter__(self):
        await self.__init_updater()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.__close_updater()

    async def __init_updater(self):
        """Initiates the telegram updater and starts polling"""
        if self._telegram_bot:
            self._LOGGER.info("Initiating telegram bot listener.")
            self.__telegram_que = asyncio.Queue()
            self.__updater = telegram.ext.Updater(
                self._telegram_bot, update_queue=self.__telegram_que)
            await self.__updater.initialize()
            await self.__updater.start_polling()
            self._LOGGER.info("Telegram bot has started listening.")

    async def __close_updater(self):
        """Close the telegram updater"""
        if self._telegram_bot:
            await self.__updater.stop()
            self._LOGGER.info("Terminating telegram bot listener.")
