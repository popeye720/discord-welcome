import os
import discord
from discord.ext import commands

IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class SimpleEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def embed(self, ctx, *, message: str):

        # 🔒 owner only check
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Sirf owner hi ye command use kar sakta hai.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()  # yellow
        )

        # 🖼️ image from ENV (safe)
        if IMAGE_URL.startswith("http"):
            embed.set_image(url=IMAGE_URL)

        # 👤 niche avatar (footer)
        embed.set_footer(
            text=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SimpleEmbed(bot))
2