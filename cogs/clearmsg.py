import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, *channel_ids: int):
        # Owner-only check
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        # Validate number of IDs
        if not channel_ids:
            return await ctx.send("❌ Please provide at least one channel ID.")
        if len(channel_ids) > 3:
            return await ctx.send("❌ You can clear messages from a maximum of 3 channels at once.")

        results = []

        for channel_id in channel_ids:
            channel = ctx.guild.get_channel(channel_id)

            if not channel:
                results.append(f"❌ `{channel_id}` → Invalid channel ID.")
                continue

            if channel.type == discord.ChannelType.category:
                results.append(f"❌ {channel.name} → Categories cannot be cleared.")
                continue

            try:
                deleted = await channel.purge(limit=None, bulk=True)
            except discord.Forbidden:
                results.append(f"❌ {channel.mention} → Missing permissions.")
                continue
            except discord.HTTPException:
                results.append(f"❌ {channel.mention} → Failed due to an API error.")
                continue

            if not deleted:
                results.append(f"ℹ️ {channel.mention} → No messages to delete.")
            else:
                results.append(
                    f"✅ {channel.mention} → Deleted {len(deleted)} messages."
                )

        # Send combined result message
        await ctx.send("\n".join(results))

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
