import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class DMForward(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ❌ ignore bot messages
        if message.author.bot:
            return

        # ❌ only DM messages
        if message.guild is not None:
            return

        # ❌ owner id missing
        if OWNER_ID == 0:
            return

        owner = self.bot.get_user(OWNER_ID)
        if not owner:
            owner = await self.bot.fetch_user(OWNER_ID)

        # 📨 basic text
        content = message.content or "*[No text]*"

        embed = discord.Embed(
            title="📩 New DM received",
            description=content,
            color=discord.Color.blurple()
        )
        embed.set_author(
            name=f"{message.author} ({message.author.id})",
            icon_url=message.author.display_avatar.url
        )

        await owner.send(embed=embed)

        # 📎 attachments (photo / video / files)
        for attachment in message.attachments:
            await owner.send(
                content=f"📎 Attachment from **{message.author}**",
                file=await attachment.to_file()
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DMForward(bot))