"""
Telegram Bot Module — handles sending messages via the Telegram Bot API.
Uses python-telegram-bot library.
"""

import logging
from typing import Union
from telegram import Bot
from telegram.error import TelegramError, InvalidToken, Forbidden, RetryAfter

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """Handles Telegram bot operations with Bot instance reuse."""

    def __init__(self):
        
        self._bots: dict[str, Bot] = {}

    def _get_bot(self, token: str) -> Bot:
        """Return a cached Bot instance for the given token."""
        if token not in self._bots:
            self._bots[token] = Bot(token=token)
        return self._bots[token]

    async def send_message(
        self,
        token: str,
        chat_id: Union[str, int],
        message: str,
        parse_mode: str = "HTML",
    ) -> dict:
        """
        Send a message to a specific Telegram chat/channel.

        Args:
            token: Bot token from @BotFather
            chat_id: Target chat/channel ID (int) or username (str, e.g. '@channel')
            message: Message content to send
            parse_mode: Telegram parse mode — 'HTML' or 'MarkdownV2'

        Returns:
            dict with 'status' and 'detail' keys
        """
        try:
            bot = self._get_bot(token)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)

            logger.info("Telegram message sent to chat %s", chat_id)
            return {"status": "success", "detail": f"Message sent to chat {chat_id}"}

        except InvalidToken:
            logger.error("Invalid Telegram bot token")
            return {"status": "failed", "detail": "Invalid bot token"}

        except Forbidden:
            logger.error("Bot blocked or chat not found: %s", chat_id)
            return {"status": "failed", "detail": "Bot is blocked or chat not found"}

        except RetryAfter as e:
            logger.warning("Telegram rate limit hit, retry after %s seconds", e.retry_after)
            return {"status": "failed", "detail": f"Rate limited — retry after {e.retry_after}s"}

        except TelegramError as e:
            logger.error("Telegram API error: %s", e)
            return {"status": "failed", "detail": str(e)}

        except Exception as e:
            logger.exception("Unexpected error sending Telegram message")
            return {"status": "failed", "detail": str(e)}

    async def validate_token(self, token: str) -> bool:
        """Validate a Telegram bot token by calling getMe."""
        try:
            bot = self._get_bot(token)
            user = await bot.get_me()
            return user is not None
        except Exception:
            logger.warning("Telegram token validation failed")
            return False

    async def get_bot_info(self, token: str) -> dict:
        """
        Get information about the bot.

        Returns:
            dict with bot details, or raises on failure
        """
        bot = self._get_bot(token)
        user = await bot.get_me()  
        return {
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "is_bot": user.is_bot,
        }

    async def close_all(self):
        """Shut down all cached bot sessions gracefully."""
        for bot in self._bots.values():
            await bot.shutdown()
        self._bots.clear()


# Singleton instance
telegram_handler = TelegramBotHandler()