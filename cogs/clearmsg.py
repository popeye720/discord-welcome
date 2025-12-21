import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, channel_id: int):
        # 🔒 Owner-only check
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        # 🧹 Delete messages
        try:
            deleted = await channel.purge(limit=None)
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to delete messages.")
        except discord.HTTPException:
            return await ctx.send("❌ Failed to delete messages.")

        await ctx.send(
            f"✅ Deleted **{len(deleted)}** messages from {channel.mention}"
        )

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
