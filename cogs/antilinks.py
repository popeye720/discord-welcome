import os
import re
import discord
from discord.ext import commands
import asyncio   # ✅ ADD THIS

LINK_REGEX = re.compile(
    r"(https?:\/\/|www\.)\S+",
    re.IGNORECASE
)

ALLOWED_CHANNEL_LINKS = int(os.getenv("ALLOWED_CHANNEL_LINKS", 0))
OWNER_ID = int(os.getenv("OWNER_ID", 0))

class Protection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots
        if message.author.bot:
            return

        # Ignore DMs
        if not message.guild:
            return

        # Owner can send links anywhere
        if message.author.id == OWNER_ID:
            return

        # Detect link
        if LINK_REGEX.search(message.content):

            # ✅ Allowed channel → delete after 2 minutes
            if message.channel.id == ALLOWED_CHANNEL_LINKS:
                try:
                    await asyncio.sleep(120)  # 2 minutes
                    await message.delete()
                except:
                    pass
                return

            # ❌ Other channels → instant delete
            try:
                await message.delete()
            except discord.Forbidden:
                return

            # DM the user
            try:
                embed = discord.Embed(
                    title="🚫 Link Not Allowed",
                    description=(
                        f"Hello **{message.author.name}**, 👋\n\n"
                        "**Links are not allowed in this server.**\n\n"
                    ),
                    color=discord.Color.red()
                )
                await message.author.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs closed

async def setup(bot):
    await bot.add_cog(Protection(bot))
