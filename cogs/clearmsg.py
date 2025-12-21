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

        notify_channel = ctx.channel  # ✅ SAFE CHANNEL FOR UPDATES

        # ❌ Voice channel
        if isinstance(channel, discord.VoiceChannel):
            return await notify_channel.send(
                "❌ Ye voice channel hai. VC ke messages clear karne ke baad notify nahi hota."
            )

        if not isinstance(channel, discord.TextChannel):
            return await notify_channel.send("❌ Ye text channel nahi hai.")

        # 📭 Message check
        async for _ in channel.history(limit=1):
            break
        else:
            return await notify_channel.send(
                f"ℹ️ {channel.mention} me koi message hi nahi hai."
            )

        # Save data
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

        # ✅ Notification guaranteed
        await notify_channel.send(
            f"✅ Channel successfully cleared: {new_channel.mention}"
        )

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
