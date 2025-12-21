import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, channel_id: int):
        # Owner-only check
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        # Skip categories
        if channel.type == discord.ChannelType.category:
            return await ctx.send("❌ Messages cannot be cleared from a category.")

        # Fast bulk delete (Text + Voice channel chats)
        try:
            deleted = await channel.purge(limit=None, bulk=True)
        except discord.Forbidden:
            return await ctx.send(
                "❌ I do not have permission to delete messages in that channel."
            )

        if not deleted:
            return await ctx.send(
                f"ℹ️ There are no messages to delete in {channel.mention}."
            )

        await ctx.send(
            f"✅ Successfully deleted {len(deleted)} messages in {channel.mention}."
        )

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
