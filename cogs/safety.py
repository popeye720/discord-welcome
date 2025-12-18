import discord
from discord.ext import commands
import time
from datetime import timedelta
import asyncio

class Safety(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # user_id : list of (timestamp, message)
        self.user_messages = {}

        self.MESSAGE_LIMIT = 5
        self.TIME_WINDOW = 6
        self.TIMEOUT_SECONDS = 120

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

        user_id = message.author.id
        now = time.time()

        # ===== LINK DETECTION =====
        if any(link in message.content.lower() for link in self.LINK_KEYWORDS):
            try:
                await message.delete()
            except:
                pass

        # ===== STORE MESSAGE FOR SPAM CHECK =====
        msgs = self.user_messages.get(user_id, [])
        msgs.append((now, message))

        # keep only recent messages
        msgs = [(t, m) for t, m in msgs if now - t <= self.TIME_WINDOW]
        self.user_messages[user_id] = msgs

        # ===== SPAM TRIGGER =====
        if len(msgs) >= self.MESSAGE_LIMIT:
            try:
                # timeout user
                await message.author.timeout(
                    timedelta(seconds=self.TIMEOUT_SECONDS),
                    reason="Spam detected"
                )

                # delete all spam messages (recent only)
                for _, msg in msgs:
                    try:
                        await msg.delete()
                    except:
                        pass

                # warning in same channel
                embed = discord.Embed(
                    description=(
                        "⚠️ **Spam Detected**\n\n"
                        f"{message.author.mention}, you were sending messages too fast.\n\n"
                        f"⏳ **Timeout:** {self.TIMEOUT_SECONDS} seconds\n"
                        "Please slow down."
                    ),
                    color=discord.Color.red()
                )

                warn = await message.channel.send(embed=embed)
                await asyncio.sleep(6)
                await warn.delete()

            except:
                pass

            # reset stored messages
            self.user_messages[user_id] = []
            return

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Safety(bot))
