import os
import discord
from discord.ext import commands
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID"))

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = {}  # guild_id -> session data

    def is_owner(self, ctx):
        return ctx.author.id == OWNER_ID

    @commands.command(name="record")
    async def record(self, ctx, user: discord.Member, minutes: int):
        if not self.is_owner(ctx):
            return await ctx.reply("❌ This command is owner-only.")

        if not user.voice or not user.voice.channel:
            return await ctx.reply("❌ User is not in a voice channel.")

        if minutes <= 0 or minutes > 10:
            return await ctx.reply("❌ Duration must be between 1 and 10 minutes.")

        channel = user.voice.channel
        vc = await channel.connect()

        # IMPORTANT: wait for voice to be ready
        await asyncio.sleep(2)

        sink = discord.sinks.WaveSink()

        self.active[ctx.guild.id] = {
            "ctx": ctx,
            "user": user,
            "vc": vc,
            "sink": sink,
            "stopped": False,
        }

        await ctx.send(
            f"🎙️ **Recording started**\n"
            f"👤 User: {user.mention}\n"
            f"⏱ Duration: {minutes} minutes"
        )

        vc.start_recording(
            sink,
            self._on_finish,
            ctx.guild.id
        )

        try:
            await asyncio.sleep(minutes * 60)
        finally:
            # Force stop if still active
            session = self.active.get(ctx.guild.id)
            if session and not session["stopped"]:
                vc.stop_recording()

    async def _on_finish(self, sink, guild_id):
        session = self.active.pop(guild_id, None)
        if not session:
            return

        ctx = session["ctx"]
        user = session["user"]
        vc = session["vc"]

        session["stopped"] = True

        if vc:
            await vc.disconnect()

        audio = sink.audio_data.get(user.id)

        owner = await self.bot.fetch_user(OWNER_ID)

        if audio:
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

            await ctx.send("✅ **Recording completed and sent to owner DM.**")
        else:
            await ctx.send("⚠️ **Recording stopped, but no audio was captured.**")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        session = self.active.get(member.guild.id)
        if not session:
            return

        # If the recorded user leaves VC early
        if member.id == session["user"].id and before.channel and not after.channel:
            vc = session["vc"]
            if vc and vc.is_recording():
                vc.stop_recording()

async def setup(bot):
    await bot.add_cog(Recorder(bot))
