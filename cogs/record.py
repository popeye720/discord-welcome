import os
import discord
from discord.ext import commands
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID"))

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_recordings = {}  # guild_id -> data

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

        sink = discord.sinks.WaveSink()

        self.active_recordings[ctx.guild.id] = {
            "vc": vc,
            "sink": sink,
            "ctx": ctx,
            "user": user,
        }

        await ctx.send(
            f"🎙️ **Recording started**\n"
            f"👤 User: {user.mention}\n"
            f"⏱ Duration: {minutes} minutes"
        )

        vc.start_recording(
            sink,
            self.recording_finished,
            ctx.guild.id
        )

        # Max duration timer
        await asyncio.sleep(minutes * 60)

        if ctx.guild.id in self.active_recordings:
            vc.stop_recording()

    async def recording_finished(self, sink, guild_id):
        data = self.active_recordings.pop(guild_id, None)
        if not data:
            return

        ctx = data["ctx"]
        user = data["user"]
        vc = data["vc"]

        if vc:
            await vc.disconnect()

        audio = sink.audio_data.get(user.id)
        if not audio:
            await ctx.send("❌ Recording stopped, but no audio was captured.")
            return

        owner = await self.bot.fetch_user(OWNER_ID)

        file = discord.File(
            audio.file,
            filename=f"{user.id}_recording.wav"
        )

        await owner.send(
            content=(
                "🎧 **Recording Finished**\n"
                f"👤 User: {user}\n"
                f"📁 Format: WAV (HD)"
            ),
            file=file
        )

        await ctx.send("✅ **Recording finished and sent to owner DM.**")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild.id not in self.active_recordings:
            return

        data = self.active_recordings[member.guild.id]
        target_user = data["user"]
        vc = data["vc"]

        # If the recorded user leaves voice
        if member.id == target_user.id and before.channel and not after.channel:
            if vc and vc.is_recording():
                vc.stop_recording()

async def setup(bot):
    await bot.add_cog(Recorder(bot))
