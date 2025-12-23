import os
import discord
from discord.ext import commands
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID"))

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # guild_id -> data

    def owner_only(self, ctx):
        return ctx.author.id == OWNER_ID

    @commands.command()
    async def record(self, ctx, member: discord.Member, minutes: int):
        if not self.owner_only(ctx):
            return await ctx.reply("❌ Owner only command")

        if not member.voice or not member.voice.channel:
            return await ctx.reply("❌ User is not in voice")

        if minutes < 1 or minutes > 10:
            return await ctx.reply("❌ Max 10 minutes allowed")

        # 🚫 Stop music player if exists
        if ctx.voice_client:
            await ctx.voice_client.disconnect(force=True)

        channel = member.voice.channel
        vc = await channel.connect()

        sink = discord.sinks.WaveSink()

        self.sessions[ctx.guild.id] = {
            "vc": vc,
            "user": member,
            "ctx": ctx
        }

        owner = await self.bot.fetch_user(OWNER_ID)

        # ✅ CONFIRMATION DM
        await owner.send(
            f"🎙️ **Recording Started**\n"
            f"👤 User: {member}\n"
            f"⏱ Duration: {minutes} min"
        )

        await ctx.send(
            f"🎙️ Recording started for {member.mention} "
            f"({minutes} min)"
        )

        vc.start_recording(
            sink,
            self.recording_finished,
            ctx.guild.id
        )

        await asyncio.sleep(minutes * 60)

        if vc.is_recording():
            vc.stop_recording()

    # ⚠️ MUST NOT BE ASYNC
    def recording_finished(self, sink, guild_id):
        self.bot.loop.create_task(
            self.handle_finish(sink, guild_id)
        )

    async def handle_finish(self, sink, guild_id):
        data = self.sessions.pop(guild_id, None)
        if not data:
            return

        vc = data["vc"]
        user = data["user"]
        ctx = data["ctx"]

        await vc.disconnect()

        owner = await self.bot.fetch_user(OWNER_ID)

        audio = sink.audio_data.get(user.id)

        if not audio:
            await ctx.send("⚠️ No audio captured")
            await owner.send("⚠️ Recording failed – no audio")
            return

        file = discord.File(
            audio.file,
            filename=f"{user.id}.wav"
        )

        await owner.send(
            content=(
                "✅ **Recording Finished**\n"
                f"👤 User: {user}\n"
                f"📁 WAV File"
            ),
            file=file
        )

        await ctx.send("✅ Recording sent to owner DM")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        data = self.sessions.get(member.guild.id)
        if not data:
            return

        if member.id == data["user"].id and before.channel and not after.channel:
            vc = data["vc"]
            if vc and vc.is_recording():
                vc.stop_recording()

async def setup(bot):
    await bot.add_cog(Recorder(bot))
