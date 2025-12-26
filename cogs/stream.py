import discord
from discord.ext import commands
import os
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ================= AUTO DELETE HELPER =================

async def auto_delete_pair(ctx, bot_text: str, delay: int = 3):
    try:
        bot_msg = await ctx.send(bot_text)
        await asyncio.sleep(delay)
        await ctx.message.delete()
        await bot_msg.delete()
    except:
        pass


# ================= STREAM MODE COG =================

class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="streammode")
    async def streammode(self, ctx):

        if ctx.author.id != OWNER_ID:
            return await auto_delete_pair(
                ctx,
                "❌ Only owner can enable stream mode.",
                delay=3
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await auto_delete_pair(
                ctx,
                "❌ Join a voice channel first.",
                delay=3
            )

        vc = ctx.author.voice.channel
        self.bot.blocked_voice_channel_id = vc.id

        # If bot already in that VC → leave
        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        await auto_delete_pair(
            ctx,
            f"🔒 **Stream Mode ON**\nBot will never join **{vc.name}**",
            delay=5
        )

    @commands.command(name="streamoff")
    async def streamoff(self, ctx):

        if ctx.author.id != OWNER_ID:
            return await auto_delete_pair(
                ctx,
                "❌ Only owner can disable stream mode.",
                delay=3
            )

        self.bot.blocked_voice_channel_id = None

        await auto_delete_pair(
            ctx,
            "🔓 **Stream Mode OFF** — bot can join voice channels now.",
            delay=5
        )


async def setup(bot):
    await bot.add_cog(StreamMode(bot))
