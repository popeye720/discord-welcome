import discord
from discord.ext import commands
import asyncio
import os
import edge_tts
from datetime import datetime
from database.mongo import db

locks = db.voice_speak_locks

class VoiceSpeak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_tts(self, text, file_path):
        communicate = edge_tts.Communicate(
            text=text,
            voice="en-IN-NeerjaNeural"  # Female voice
        )
        await communicate.save(file_path)

    @commands.command(name="speak")
    @commands.has_guild_permissions(administrator=True)
    async def speak(self, ctx, *, words: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("You must be in a voice channel.")

        guild_id = ctx.guild.id
        user_id = ctx.author.id

        lock = locks.find_one({"guild_id": guild_id})
        if lock and lock.get("active"):
            return await ctx.reply("Speak command is already in use.")

        locks.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "guild_id": guild_id,
                    "active": True,
                    "user_id": user_id,
                    "started_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        vc = ctx.author.voice.channel
        voice_client = None
        audio_file = f"/tmp/{guild_id}_tts.mp3"

        try:
            await self.generate_tts(words, audio_file)

            voice_client = await vc.connect()
            source = discord.FFmpegPCMAudio(audio_file)

            voice_client.play(source)

            while voice_client.is_playing():
                await asyncio.sleep(1)

        except Exception as e:
            await ctx.reply("Failed to speak text.")
            print(e)

        finally:
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()

            if os.path.exists(audio_file):
                os.remove(audio_file)

            locks.delete_one({"guild_id": guild_id})

    @speak.error
    async def speak_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need admin permission to use this command.")

async def setup(bot):
    await bot.add_cog(VoiceSpeak(bot))
