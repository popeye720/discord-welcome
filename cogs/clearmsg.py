import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, channel_id: int):
        # 🔒 Owner-only
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        category = channel.category
        position = channel.position
        overwrites = channel.overwrites
        name = channel.name
        topic = channel.topic
        slowmode = channel.slowmode_delay

        await channel.delete(reason="Owner requested fast clear")

        new_channel = await ctx.guild.create_text_channel(
            name=name,
            category=category,
            position=position,
            topic=topic,
            slowmode_delay=slowmode,
            overwrites=overwrites
        )

        await ctx.send(
            f"✅ Channel fully cleared instantly: {new_channel.mention}"
        )

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
