import discord
from discord.ext import commands
import time
from datetime import timedelta
import asyncio

class Safety(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = {}

        self.MESSAGE_LIMIT = 5
        self.TIME_WINDOW = 6
        self.TIMEOUT_SECONDS = 60

        self.LINK_KEYWORDS = [
            "http://",
            "https://",
            "discord.gg/",
            "discord.com/invite"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # ===== LINK DETECTION =====
        content_lower = message.content.lower()
        if any(link in content_lower for link in self.LINK_KEYWORDS):
            try:
                await message.delete()
            except:
                pass

        # ===== SPAM DETECTION =====
        user_id = message.author.id
        now = time.time()

        timestamps = self.user_messages.get(user_id, [])
        timestamps.append(now)

        timestamps = [t for t in timestamps if now - t <= self.TIME_WINDOW]
        self.user_messages[user_id] = timestamps

        if len(timestamps) >= self.MESSAGE_LIMIT:
            try:
                await message.delete()

                # timeout user
                await message.author.timeout(
                    timedelta(seconds=self.TIMEOUT_SECONDS),
                    reason="Spam detected"
                )

                # ===== CHAT WARNING (AUTO DELETE) =====
                embed = discord.Embed(
                    description=(
                        "⚠️ **Spam Detected**\n\n"
                        f"{message.author.mention}, you were sending messages too fast.\n\n"
                        f"⏳ **Timeout:** {self.TIMEOUT_SECONDS} seconds\n"
                        "Please slow down."
                    ),
                    color=discord.Color.red()
                )

                warn_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(6)
                await warn_msg.delete()

            except:
                pass

            self.user_messages[user_id] = []
            return

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Safety(bot))
