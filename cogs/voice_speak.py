import discord
from discord.ext import commands
import asyncio
import os
import edge_tts

# 🔒 Per-server lock (guild_id based)
guild_locks = {}

class VoiceSpeak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_tts(self, text, file_path):
        print("[TTS] Generating voice...")
        communicate = edge_tts.Communicate(
            text=text,
            voice="en-IN-NeerjaNeural"  # Female voice
        )
        await communicate.save(file_path)
        print("[TTS] Voice generated successfully")

    @commands.command(name="speak")
    @commands.has_guild_permissions(administrator=True)
    async def speak(self, ctx, *, words: str):
        guild_id = ctx.guild.id

        print(f"[SPEAK] Used by {ctx.author} in {ctx.guild.name}")

        # 🔒 Same-server lock
        if guild_locks.get(guild_id):
            print("[LOCK] Speak already running in this server")
            return await ctx.reply("Already speaking in this server. Wait.")

        if not ctx.author.voice or not ctx.author.voice.channel:
            print("[ERROR] User not in VC")
            return await ctx.reply("You must be in a voice channel.")

        guild_locks[guild_id] = True

        vc = ctx.author.voice.channel
        voice_client = None
        audio_file = f"/tmp/tts_{guild_id}.mp3"

        try:
            # 1️⃣ Generate TTS
            await self.generate_tts(words, audio_file)

            if not os.path.exists(audio_file):
                print("[ERROR] Audio file missing")
                return await ctx.reply("TTS audio failed.")

            # 2️⃣ Connect to VC
            print("[VC] Connecting...")
            voice_client = ctx.voice_client
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(vc)
            else:
                voice_client = await vc.connect(timeout=20)

            await asyncio.sleep(1)

            # 3️⃣ Play audio
            print("[AUDIO] Playing voice")

            def after_play(err):
                if err:
                    print("[FFMPEG ERROR]", err)

            source = discord.FFmpegPCMAudio(
                audio_file,
                before_options="-nostdin",
                options="-vn"
            )

            voice_client.play(source, after=after_play)

            while voice_client.is_playing():
                await asyncio.sleep(0.5)

            print("[DONE] Audio finished")

        except Exception as e:
            print("========== SPEAK ERROR ==========")
            print(type(e))
            print(e)
            print("================================")
            await ctx.reply("Voice error. Check Railway logs.")

        finally:
            print("[CLEANUP] Cleaning up")

            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
                print("[VC] Disconnected")

            if os.path.exists(audio_file):
                os.remove(audio_file)
                print("[FILE] Audio removed")

            guild_locks.pop(guild_id, None)
            print("[LOCK] Released for this server")

    @speak.error
    async def speak_error(self, ctx, error):
        print("[COMMAND ERROR]", error)
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Admin permission required.")

async def setup(bot):
    await bot.add_cog(VoiceSpeak(bot))
