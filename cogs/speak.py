import discord
from discord.ext import commands
from discord import app_commands
import tempfile
import os
import asyncio
from gtts import gTTS
from typing import Optional

import shutil, subprocess
print("FFMPEG:", shutil.which("ffmpeg"))
subprocess.run(["ffmpeg", "-version"])

# ================= CONFIG =================
DELETE_DELAY = 5
FFMPEG_PATH = "/usr/bin/ffmpeg"   # ✅ STATIC FFMPEG (Railway-safe)
# =========================================


class Speak(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================= SLASH COMMAND =================
    @app_commands.command(
        name="speak",
        description="Make the bot speak text in a voice channel"
    )
    @app_commands.describe(
        channel="Voice channel (optional)",
        text="Text to speak"
    )
    async def speak(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: Optional[discord.VoiceChannel] = None
    ):
        await interaction.response.defer(ephemeral=True)

        # ---- Resolve Voice Channel ----
        if channel:
            target_channel = channel
        else:
            if not interaction.user.voice:
                return await interaction.followup.send(
                    "❌ Join a voice channel first.",
                    ephemeral=True
                )
            target_channel = interaction.user.voice.channel

        # ---- Connect / Move ----
        vc = interaction.guild.voice_client
        if vc and vc.channel != target_channel:
            await vc.move_to(target_channel)
        elif not vc:
            vc = await target_channel.connect()

        # ---- Create TTS File ----
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            gTTS(text=text, lang="hi").save(f.name)
            audio_path = f.name

        # ---- After Playback ----
        def after_playing(error):
            try:
                os.remove(audio_path)
            except:
                pass

            asyncio.run_coroutine_threadsafe(
                vc.disconnect(),
                self.bot.loop
            )

            if error:
                print("FFMPEG ERROR:", error)

        # ---- Play Audio ----
        source = discord.FFmpegPCMAudio(
            audio_path,
            executable=FFMPEG_PATH,
            options="-loglevel warning -filter:a volume=3.0"
        )

        vc.play(source, after=after_playing)

        await interaction.followup.send(
            f"🗣️ Speaking in **{target_channel.name}**",
            ephemeral=True
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Speak(bot))