import discord
from discord.ext import commands
from discord import app_commands
import tempfile
import os
import asyncio
from gtts import gTTS
from typing import Optional
import shutil
import traceback
import time
import subprocess

FFMPEG_PATH = "/usr/bin/ffmpeg"


class Speak(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("========== SPEAK COG INIT ==========")
        print("FFMPEG WHICH:", shutil.which("ffmpeg"))
        print("FFMPEG PATH VAR:", FFMPEG_PATH)
        print("===================================")

    @app_commands.command(
        name="speak",
        description="Make the bot speak text in a voice channel (DEBUG MODE)"
    )
    async def speak(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: Optional[discord.VoiceChannel] = None
    ):
        print("\n========== /SPEAK CALLED ==========")
        print("User:", interaction.user)
        print("Guild:", interaction.guild)
        print("Text:", text)
        print("Channel param:", channel)

        try:
            print("Deferring interaction...")
            await interaction.response.defer(ephemeral=True)
            print("Deferred OK")

            # ---------- Voice channel ----------
            if channel:
                target = channel
                print("Using provided voice channel:", target.name)
            else:
                print("No channel provided, checking user voice...")
                if not interaction.user.voice:
                    print("❌ User not in voice")
                    return await interaction.followup.send(
                        "❌ Join a voice channel first.",
                        ephemeral=True
                    )
                target = interaction.user.voice.channel
                print("Resolved user voice channel:", target.name)

            # ---------- Voice client ----------
            vc = interaction.guild.voice_client
            print("Existing VC:", vc)

            if vc and vc.channel != target:
                print("Moving bot to channel:", target.name)
                await vc.move_to(target)
                print("Move OK")
            elif not vc:
                print("Connecting bot to channel:", target.name)
                vc = await target.connect()
                print("Connected OK")

            print("VC connected:", vc, "Channel:", vc.channel)

            if vc.is_playing():
                print("VC already playing, stopping...")
                vc.stop()

            # ---------- Temp file ----------
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp.close()
            print("Temp MP3 created:", tmp.name)

            # ---------- gTTS ----------
            print("Starting gTTS generation...")
            start = time.time()

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: gTTS(text=text, lang="hi").save(tmp.name)
            )

            print("gTTS DONE in", round(time.time() - start, 2), "seconds")
            print("MP3 file size:", os.path.getsize(tmp.name), "bytes")

            # ---------- Test ffmpeg manually ----------
            print("Testing ffmpeg on file...")
            test = subprocess.run(
                [FFMPEG_PATH, "-i", tmp.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("FFMPEG TEST RETURN CODE:", test.returncode)
            print("FFMPEG STDERR:\n", test.stderr[:1000])

            # ---------- Play ----------
            print("Creating FFmpegPCMAudio source...")
            source = discord.FFmpegPCMAudio(
                tmp.name,
                executable=FFMPEG_PATH,
                before_options="-nostdin",
                options="-loglevel debug"
            )

            print("Calling vc.play() ...")
            vc.play(source)
            print("vc.play() called")

            await interaction.followup.send(
                f"🗣️ Speaking in **{target.name}**",
                ephemeral=True
            )
            print("Followup sent")

            # ---------- Monitor playback ----------
            print("Waiting for playback to finish...")
            while True:
                playing = vc.is_playing()
                print("is_playing =", playing)
                if not playing:
                    break
                await asyncio.sleep(0.5)

            print("Playback finished")

            print("Disconnecting VC...")
            await vc.disconnect()
            print("Disconnected")

            try:
                os.remove(tmp.name)
                print("Temp file deleted")
            except Exception as e:
                print("Temp delete error:", e)

            print("========== /SPEAK DONE ==========\n")

        except Exception as e:
            print("========== SPEAK ERROR ==========")
            traceback.print_exc()
            print("================================")

            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Error while speaking. Check Railway logs.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Error while speaking. Check Railway logs.",
                    ephemeral=True
                )


async def setup(bot: commands.Bot):
    print("Loading Speak cog...")
    await bot.add_cog(Speak(bot))
    print("Speak cog loaded")