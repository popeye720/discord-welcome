import discord
from discord.ext import commands
import asyncio
import os
import edge_tts
import shutil

# 🔒 Per-server lock
guild_locks = {}

class VoiceSpeak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        ffmpeg_path = shutil.which("ffmpeg")
        print("[DEBUG] ffmpeg path:", ffmpeg_path)

        if not ffmpeg_path:
            print("⚠️ WARNING: FFMPEG not found at startup")

    async def generate_tts(self, text, file_path):
        print("[TTS] Generating voice...")
        communicate = edge_tts.Communicate(
            text=text,
            voice="en-IN-NeerjaNeural"
        )
        await communicate.save(file_path)
        print("[TTS] Voice generated successfully")

    @commands.command(name="speak")
    @commands.has_guild_permissions(administrator=True)
    async def speak(self, ctx, *, words: str):
        guild_id = ctx.guild.id
        print(f"[SPEAK] Used by {ctx.author} in {ctx.guild.name}")

        if guild_locks.get(guild_id):
            return await ctx.reply("Already speaking in this server.")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("You must be in a voice channel.")

        if not shutil.which("ffmpeg"):
            return await ctx.reply("❌ FFMPEG not available on server.")

        guild_locks[guild_id] = True
        vc = ctx.author.voice.channel
        voice_client = None
        audio_file = f"/tmp/tts_{guild_id}.mp3"

        try:
            await self.generate_tts(words, audio_file)

            voice_client = ctx.voice_client
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(vc)
            else:
                voice_client = await vc.connect(timeout=20)

            await asyncio.sleep(1)

            print("[AUDIO] Playing voice")

            source = discord.FFmpegPCMAudio(
                audio_file,
                before_options="-nostdin",
                options="-vn"
            )

            voice_client.play(source)

            while voice_client.is_playing():
                await asyncio.sleep(0.5)

        except Exception as e:
            print("========== SPEAK ERROR ==========")
            print(type(e), e)
            print("================================")

        finally:
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()

            if os.path.exists(audio_file):
                os.remove(audio_file)

            guild_locks.pop(guild_id, None)
            print("[LOCK] Released")

async def setup(bot):
    await bot.add_cog(VoiceSpeak(bot))
