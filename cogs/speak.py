import discord
from discord.ext import commands
import tempfile
import os
import asyncio
from gtts import gTTS
from typing import Optional

# ================= CONFIG =================

DELETE_DELAY = 5
FFMPEG_PATH = "ffmpeg"


# ========================================


class Speak(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- UTIL ----------

    async def delete_both(self, user_msg, bot_msg, delay=5):
        await asyncio.sleep(delay)
        try:
            await user_msg.delete()
        except:
            pass
        try:
            await bot_msg.delete()
        except:
            pass

    # ---------- SPEAK COMMAND ----------

    @commands.command(name="speak")
    async def speak(
        self,
        ctx: commands.Context,
        vc_id: Optional[int] = None,
        *,
        text: str = None
    ):
        if text is None:
            bot_msg = await ctx.send(
                "Usage:\n`speak <text>` OR `speak <voice_channel_id> <text>`"
            )
            return await self.delete_both(ctx.message, bot_msg, DELETE_DELAY)

        # ----- VOICE CHANNEL RESOLUTION -----
        if vc_id:
            channel = ctx.guild.get_channel(vc_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                bot_msg = await ctx.send("Invalid voice channel ID.")
                return await self.delete_both(ctx.message, bot_msg, DELETE_DELAY)
        else:
            if not ctx.author.voice:
                bot_msg = await ctx.send("Join a voice channel first.")
                return await self.delete_both(ctx.message, bot_msg, DELETE_DELAY)
            channel = ctx.author.voice.channel

        await self.play_voice(ctx, channel, text)

    # ---------- VOICE LOGIC ----------

    async def play_voice(self, ctx, channel, text):
        vc = ctx.voice_client

        if vc and vc.channel != channel:
            await vc.move_to(channel)
        elif not vc:
            vc = await channel.connect()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            gTTS(text=text, lang="hi").save(f.name)
            audio_path = f.name

        def after_playing(error):
            try:
                os.remove(audio_path)
            except:
                pass
            asyncio.run_coroutine_threadsafe(
                vc.disconnect(),
                self.bot.loop
            )

        vc.play(
            discord.FFmpegPCMAudio(
                audio_path,
                executable=FFMPEG_PATH,
                options="-filter:a volume=3.0"
            ),
            after=after_playing
        )

        bot_msg = await ctx.send(f"Speaking: `{text}`")
        await self.delete_both(ctx.message, bot_msg, DELETE_DELAY)


# ---------- SETUP ----------

async def setup(bot: commands.Bot):
    await bot.add_cog(Speak(bot))
