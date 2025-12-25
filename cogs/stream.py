import discord
from discord.ext import commands
import os

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="streammode")
    async def streammode(self, ctx):
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only owner can enable stream mode.")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Join a voice channel first.")

        vc = ctx.author.voice.channel
        self.bot.blocked_voice_channel_id = vc.id

        # If bot is already in that VC → leave immediately
        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        await ctx.send(
            f"🔒 **Stream Mode ON**\n"
            f"Bot will never join **{vc.name}**"
        )

    @commands.command(name="streamoff")
    async def streamoff(self, ctx):
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only owner can disable stream mode.")

        self.bot.blocked_voice_channel_id = None
        await ctx.send("🔓 **Stream Mode OFF** — bot can join voice channels now.")

async def setup(bot):
    await bot.add_cog(StreamMode(bot))
