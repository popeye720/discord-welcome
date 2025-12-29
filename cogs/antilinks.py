import re
import discord
from discord.ext import commands

LINK_REGEX = re.compile(
    r"(https?:\/\/|www\.)\S+",
    re.IGNORECASE
)

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

        # 🔥 Server owner can send links anywhere
        if message.author.id == message.guild.owner_id:
            return

        # 🚫 Detect link → delete everywhere
        if LINK_REGEX.search(message.content):
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
                        "**Links are not allowed anywhere in this server.**\n\n"
                        "Only the **server owner** is allowed to send links."
                    ),
                    color=discord.Color.red()
                )
                await message.author.send(embed=embed)
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(Protection(bot))
