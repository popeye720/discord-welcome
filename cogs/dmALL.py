import os
import discord
from discord.ext import commands

IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class DMAll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dm")
    async def dm_all(self, ctx, *, message: str):
        # 🔒 Owner only
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        await ctx.send("📨 Sending DMs to all members...")

        sent = 0
        failed = 0

        for member in ctx.guild.members:
            # Skip bots
            if member.bot:
                continue

            embed = discord.Embed(
                description=message,
                color=discord.Color.gold()
            )

            # 🖼️ Thumbnail + Image
            if IMAGE_URL.startswith("http"):
                embed.set_thumbnail(url=IMAGE_URL)
                embed.set_image(url=IMAGE_URL)

            # 👤 Footer (avatar only)
            embed.set_footer(icon_url=ctx.author.display_avatar.url)

            try:
                await member.send(embed=embed)
                sent += 1
            except discord.Forbidden:
                failed += 1
            except Exception:
                failed += 1

        await ctx.send(
            f"✅ **DM Completed**\n"
            f"📨 Sent: `{sent}` users\n"
            f"❌ Failed: `{failed}` users"
        )

async def setup(bot):
    await bot.add_cog(DMAll(bot))
