"""
Discord Bot Module — handles sending messages and managing Discord interactions.
Uses discord.py library.
"""

import discord
import asyncio
from typing import Optional


class DiscordBotHandler:
    """Handles Discord bot operations."""

    def __init__(self):
        self.clients = {}  # token -> discord.Client mapping

    async def send_message(self, token: str, channel_id: str, message: str) -> dict:
        """
        Send a message to a specific Discord channel.

        Args:
            token: Bot token for authentication
            channel_id: Target channel ID
            message: Message content to send

        Returns:
            dict with status and details
        """
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)

            result = {"status": "failed", "detail": ""}

            @client.event
            async def on_ready():
                try:
                    channel = client.get_channel(int(channel_id))
                    if channel is None:
                        channel = await client.fetch_channel(int(channel_id))

                    await channel.send(message)
                    result["status"] = "success"
                    result["detail"] = f"Message sent to channel {channel_id}"
                    print(f"✅ [Discord] Message sent to #{channel.name}")
                except discord.NotFound:
                    result["detail"] = f"Channel {channel_id} not found"
                    print(f"❌ [Discord] Channel {channel_id} not found")
                except discord.Forbidden:
                    result["detail"] = "Bot lacks permissions to send messages"
                    print(f"❌ [Discord] Permission denied for channel {channel_id}")
                except Exception as e:
                    result["detail"] = str(e)
                    print(f"❌ [Discord] Error: {e}")
                finally:
                    await client.close()

            # Run the client with a timeout
            try:
                await asyncio.wait_for(client.start(token), timeout=30.0)
            except asyncio.TimeoutError:
                result["detail"] = "Connection timed out"
                await client.close()
            except discord.LoginFailure:
                result["detail"] = "Invalid bot token"
                result["status"] = "failed"

            return result

        except Exception as e:
            return {"status": "failed", "detail": str(e)}

    async def validate_token(self, token: str) -> bool:
        """Validate a Discord bot token by attempting to log in."""
        try:
            intents = discord.Intents.default()
            client = discord.Client(intents=intents)
            valid = False

            @client.event
            async def on_ready():
                nonlocal valid
                valid = True
                await client.close()

            try:
                await asyncio.wait_for(client.start(token), timeout=15.0)
            except (discord.LoginFailure, asyncio.TimeoutError):
                pass

            return valid
        except Exception:
            return False


# Singleton instance
discord_handler = DiscordBotHandler()
