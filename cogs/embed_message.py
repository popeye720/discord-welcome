import os
import discord
from discord.ext import commands

IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class SimpleEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="emed")
    async def emed(self, ctx, channel_id: int, *, message: str):

        # 🔒 Owner-only check
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ Image from ENV (safe)
        if IMAGE_URL.startswith("http"):
            embed.set_image(url=IMAGE_URL)

        # 👤 Footer: ONLY avatar, no text
        embed.set_footer(icon_url=ctx.author.display_avatar.url)

        await channel.send(embed=embed)
        await ctx.send(f"✅ Embedded message sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(SimpleEmbed(bot))
