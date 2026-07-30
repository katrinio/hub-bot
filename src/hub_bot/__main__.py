import asyncio
import logging
import sys

from hub_bot.bot import create_bot, create_dispatcher
from hub_bot.db import close_db, init_db
from hub_bot.db.connection import ensure_db_directory
from hub_bot.settings import get_bot_token, validate_admin_telegram_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start polling."""
    try:
        # Validate configuration early
        token = get_bot_token()
        validate_admin_telegram_id()

        # Ensure database directory exists
        ensure_db_directory()

        # Initialize database
        await init_db()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    bot = await create_bot(token)
    dp = create_dispatcher()

    logger.info("Starting polling")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Polling stopped by user")
    finally:
        await bot.session.close()
        await close_db()
        logger.info("Bot session closed")


if __name__ == "__main__":
    asyncio.run(main())
