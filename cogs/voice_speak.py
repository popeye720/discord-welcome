import discord
from discord.ext import commands
import asyncio
import os
import edge_tts

# 🔒 In-memory lock (per guild)
active_speaks = {}

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

        print(f"[SPEAK] Command used by {ctx.author} in {ctx.guild.name}")

        if not ctx.author.voice or not ctx.author.voice.channel:
            print("[ERROR] User not in voice channel")
            return await ctx.reply("You must be in a voice channel.")

        guild_id = ctx.guild.id

        # 🔒 Lock check
        if active_speaks.get(guild_id):
            print("[LOCK] Speak already running in this guild")
            return await ctx.reply("Speak command is already running.")

        active_speaks[guild_id] = True

        vc = ctx.author.voice.channel
        voice_client = None
        audio_file = f"/tmp/{guild_id}_tts.mp3"

        try:
            print("[STEP] Generating TTS file")
            await self.generate_tts(words, audio_file)

            if not os.path.exists(audio_file):
                print("[ERROR] TTS file not created")
                return await ctx.reply("TTS failed to generate audio.")

            print("[STEP] Connecting to voice channel")
            voice_client = ctx.voice_client
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(vc)
            else:
                voice_client = await vc.connect()

            print("[STEP] Playing audio")
            source = discord.FFmpegPCMAudio(audio_file)
            voice_client.play(source)

            while voice_client.is_playing():
                await asyncio.sleep(0.5)

            print("[DONE] Audio finished")

        except Exception as e:
            print("========== SPEAK ERROR ==========")
            print(type(e))
            print(e)
            print("================================")
            await ctx.reply("Error occurred. Check Railway logs.")

        finally:
            print("[CLEANUP] Cleaning resources")

            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
                print("[CLEANUP] Disconnected from VC")

            if os.path.exists(audio_file):
                os.remove(audio_file)
                print("[CLEANUP] Audio file removed")

            active_speaks.pop(guild_id, None)
            print("[LOCK] Released")

    @speak.error
    async def speak_error(self, ctx, error):
        print("[COMMAND ERROR]", error)
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Admin permission required.")

async def setup(bot):
    await bot.add_cog(VoiceSpeak(bot))
