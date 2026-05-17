"""
Discord Bot Module — handles sending messages and managing Discord interactions.
Uses discord.py library.
"""

import discord
import asyncio
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DiscordBotHandler:
    """Handles Discord bot operations with connection reuse."""

    def __init__(self):
        
        self._clients: dict[str, discord.Client] = {}

    async def _get_client(self, token: str) -> discord.Client:
        """Return a cached, logged-in client for the given token."""
        if token in self._clients:
            client = self._clients[token]
            if not client.is_closed():
                return client

        intents = discord.Intents.none()  
        client = discord.Client(intents=intents)

        ready = asyncio.get_event_loop().create_future()

        @client.event
        async def on_ready():
            if not ready.done():
                ready.set_result(True)

        asyncio.create_task(client.start(token))

        try:
            await asyncio.wait_for(asyncio.shield(ready), timeout=30.0)
        except asyncio.TimeoutError:
            await client.close()
            raise RuntimeError("Discord client timed out during login")

        self._clients[token] = client
        return client

    async def send_message(
        self,
        token: str,
        channel_id: int,
        message: str,
    ) -> dict:
        """
        Send a message to a specific Discord channel.

        Args:
            token: Bot token for authentication
            channel_id: Target channel ID (integer)
            message: Message content to send

        Returns:
            dict with 'status' and 'detail' keys
        """
        try:
            client = await self._get_client(token)

            channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
            await channel.send(message)

            logger.info("Message sent to Discord channel #%s", channel.name)
            return {"status": "success", "detail": f"Message sent to channel {channel_id}"}

        except discord.LoginFailure:
            logger.error("Invalid Discord bot token")
            return {"status": "failed", "detail": "Invalid bot token"}
        except discord.NotFound:
            logger.error("Discord channel %s not found", channel_id)
            return {"status": "failed", "detail": f"Channel {channel_id} not found"}
        except discord.Forbidden:
            logger.error("Bot lacks permission to send to channel %s", channel_id)
            return {"status": "failed", "detail": "Bot lacks permission to send messages"}
        except Exception as e:
            logger.exception("Unexpected error sending Discord message")
            return {"status": "failed", "detail": str(e)}

    async def validate_token(self, token: str) -> bool:
        """
        Validate a Discord bot token via the REST API (lightweight, no WebSocket).
        """
        url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bot {token}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    return resp.status == 200
        except Exception:
            logger.exception("Error validating Discord token")
            return False

    async def close_all(self):
        """Gracefully close all cached Discord clients."""
        for client in self._clients.values():
            if not client.is_closed():
                await client.close()
        self._clients.clear()


# Singleton instance
discord_handler = DiscordBotHandler()