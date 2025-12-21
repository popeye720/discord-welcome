import os
import discord
from discord.ext import commands

IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class Embedder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="embedder")
    async def embedder(self, ctx, channel_id: int, *, message: str):
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

        # 🖼️ SAME image → thumbnail (top-right) + image (bottom)
        if IMAGE_URL.startswith("http"):
            embed.set_thumbnail(url=IMAGE_URL)  # top-right
            embed.set_image(url=IMAGE_URL)      # bottom

        # 👤 Footer: ONLY avatar icon
        embed.set_footer(icon_url=ctx.author.display_avatar.url)

        await channel.send(embed=embed)
        await ctx.send(f"✅ Embedded message sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Embedder(bot))
