import discord
from discord.ext import commands
import os
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

async def temp_reply(ctx, text: str, delay: int = 3):
    try:
        bot_msg = await ctx.send(text)
        await asyncio.sleep(delay)
        await ctx.message.delete()
        await bot_msg.delete()
    except:
        pass


class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="streammode")
    async def streammode(self, ctx):

        if ctx.author.id != OWNER_ID:
            return await temp_reply(
                ctx,
                "❌ Only **OWNER** can enable stream mode.",
                3
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await temp_reply(
                ctx,
                "❌ Join a voice channel first.",
                3
            )

        vc = ctx.author.voice.channel
        self.bot.blocked_voice_channel_id = vc.id

        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        msg = await ctx.send(
            f"🔒 **Stream Mode ON**\n"
            f"Bot will never join **{vc.name}**"
        )

        await asyncio.sleep(4)
        await msg.delete()
        await ctx.message.delete()

    @commands.command(name="streamoff")
    async def streamoff(self, ctx):

        if ctx.author.id != OWNER_ID:
            return await temp_reply(
                ctx,
                "❌ Only **OWNER** can disable stream mode.",
                3
            )

        self.bot.blocked_voice_channel_id = None

        msg = await ctx.send("🔓 **Stream Mode OFF** — bot can join voice channels now.")
        await asyncio.sleep(4)
        await msg.delete()
        await ctx.message.delete()


async def setup(bot):
    await bot.add_cog(StreamMode(bot))
