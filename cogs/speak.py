import discord
from discord.ext import commands
from discord import app_commands
import tempfile
import os
import asyncio
from gtts import gTTS
from typing import Optional
import shutil

# ================= CONFIG =================
FFMPEG_PATH = "/usr/bin/ffmpeg"   # ✅ STATIC FFMPEG (Railway)
# =========================================


class Speak(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # ---- DEBUG (SAFE AT INIT) ----
        print("FFMPEG PATH:", shutil.which("ffmpeg"))

    # ================= SLASH COMMAND =================
    @app_commands.command(
        name="speak",
        description="Make the bot speak text in a voice channel"
    )
    @app_commands.describe(
        text="Text to speak",
        channel="Voice channel (optional)"
    )
    async def speak(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: Optional[discord.VoiceChannel] = None
    ):
        await interaction.response.defer(ephemeral=True)

        # ---------- Resolve Voice Channel ----------
        if channel:
            target_channel = channel
        else:
            if not interaction.user.voice:
                return await interaction.followup.send(
                    "❌ Join a voice channel first.",
                    ephemeral=True
                )
            target_channel = interaction.user.voice.channel

        # ---------- Connect / Move ----------
        vc = interaction.guild.voice_client
        if vc and vc.channel != target_channel:
            await vc.move_to(target_channel)
        elif not vc:
            vc = await target_channel.connect()

        # ---------- Stop if already playing ----------
        if vc.is_playing():
            vc.stop()

        # ---------- Create TTS file ----------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            gTTS(text=text, lang="hi").save(f.name)
            audio_path = f.name

        # ---------- After playback ----------
        def after_playing(error):
            if error:
                print("VOICE ERROR:", error)

            try:
                os.remove(audio_path)
            except:
                pass

            # disconnect safely
            coro = vc.disconnect()
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

        # ---------- Play audio ----------
        source = discord.FFmpegPCMAudio(
            audio_path,
            executable=FFMPEG_PATH,
            before_options="-nostdin",
            options="-loglevel error -vn"
        )

        vc.play(source, after=after_playing)

        await interaction.followup.send(
            f"🗣️ Speaking in **{target_channel.name}**",
            ephemeral=True
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Speak(bot))