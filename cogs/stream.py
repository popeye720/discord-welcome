import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID"))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stream_locked = False  # Lock flag to block VC joins

    @commands.command(name="stream")
    async def stream(self, ctx):
        # Owner-only check
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Only the bot owner can use this command.")
            return

        self.stream_locked = True
        await ctx.send("🔒 Stream mode enabled — the bot will not join any voice channel.")

    @commands.command(name="streamend")
    async def streamend(self, ctx):
        # Owner-only check
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Only the bot owner can use this command.")
            return

        # User must be in a voice channel
        if not ctx.author.voice:
            await ctx.send("❌ You are not connected to a voice channel.")
            return

        self.stream_locked = False
        voice_channel = ctx.author.voice.channel

        # If the bot is already in a voice channel
        if ctx.voice_client:
            await ctx.send("ℹ️ The bot is already connected to a voice channel.")
            return

        await voice_channel.connect()
        await ctx.send(f"✅ Stream ended — bot joined **{voice_channel.name}**")

    # Prevent the bot from joining any VC while stream is locked
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.bot.user and self.stream_locked:
            if after.channel is not None:
                await member.move_to(None)

async def setup(bot):
    await bot.add_cog(Music(bot))
