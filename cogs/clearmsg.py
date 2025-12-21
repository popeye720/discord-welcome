import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, channel_id: int):
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        # ❌ Voice / Stage channels block
        if channel.type in (
            discord.ChannelType.voice,
            discord.ChannelType.stage_voice
        ):
            return await ctx.send(
                "❌ Ye **voice channel** hai. Voice channels ke messages clear nahi kiye ja sakte."
            )

        # ❌ Extra safety
        if channel.type != discord.ChannelType.text:
            return await ctx.send("❌ Ye text channel nahi hai.")

        # 📭 Check messages
        has_msg = False
        async for _ in channel.history(limit=1):
            has_msg = True
            break

        if not has_msg:
            return await ctx.send(
                f"ℹ️ {channel.mention} me koi message hi nahi hai."
            )

        # Save settings
        data = {
            "name": channel.name,
            "category": channel.category,
            "position": channel.position,
            "topic": channel.topic,
            "slowmode_delay": channel.slowmode_delay,
            "overwrites": channel.overwrites
        }

        await channel.delete(reason="Owner requested fast clear")

        new_channel = await ctx.guild.create_text_channel(**data)

        await ctx.send(
            f"✅ Channel successfully cleared: {new_channel.mention}"
        )

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
