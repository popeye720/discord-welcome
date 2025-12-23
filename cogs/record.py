import os
import discord
from discord.ext import commands
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID"))

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recordings = {}

    def is_owner(self, ctx):
        return ctx.author.id == OWNER_ID

    @commands.command(name="record")
    async def record(self, ctx, user: discord.Member, minutes: int):
        if not self.is_owner(ctx):
            return await ctx.reply("❌ This command is owner-only.")

        if not user.voice or not user.voice.channel:
            return await ctx.reply("❌ User is not in a voice channel.")

        if minutes <= 0 or minutes > 120:
            return await ctx.reply("❌ Invalid recording duration.")

        channel = user.voice.channel
        vc = await channel.connect()

        await ctx.send(
            f"🎙️ **Recording started**\n"
            f"👤 User: {user.mention}\n"
            f"⏱ Duration: {minutes} minutes"
        )

        sink = discord.sinks.WaveSink()
        vc.start_recording(
            sink,
            self.on_record_finish,
            ctx,
            user
        )

        await asyncio.sleep(minutes * 60)
        vc.stop_recording()

    async def on_record_finish(self, sink, ctx, user):
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect()

        file = sink.audio_data.get(user.id)
        if not file:
            await ctx.send("❌ No audio captured.")
            return

        owner = await self.bot.fetch_user(OWNER_ID)

        audio_file = discord.File(file.file, filename=f"{user.id}_recording.wav")

        await owner.send(
            content=(
                "🎧 **Recording Finished**\n"
                f"👤 User: {user}\n"
                f"📁 Format: WAV (HD)"
            ),
            file=audio_file
        )

        await ctx.send("✅ **Recording completed and sent to owner DM.**")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
