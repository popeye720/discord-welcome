import discord
from discord.ext import commands
import yt_dlp
import asyncio

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "noplaylist": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.loop = False
        self.volume = 0.5

    async def play_next(self, ctx):
        if not self.queue:
            return

        source = self.queue[0]
        if not self.loop:
            self.queue.pop(0)

        vc = ctx.voice_client
        vc.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(source["url"], **FFMPEG_OPTIONS),
                volume=self.volume,
            ),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(ctx), self.bot.loop
            ),
        )

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()

    @commands.command()
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Voice channel join karo pehle")

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        data = ytdl.extract_info(query, download=False)
        if "entries" in data:
            data = data["entries"][0]

        self.queue.append({
            "title": data["title"],
            "url": data["url"]
        })

        await ctx.send(f"▶️ **Playing:** {data['title']}")

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.pause()
            await ctx.send("⏸️ Paused")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.resume()
            await ctx.send("▶️ Resumed")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.send("⏭️ Skipped")

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            self.queue.clear()
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            await ctx.send("⏹️ Stopped")

    @commands.command()
    async def loop(self, ctx):
        self.loop = not self.loop
        await ctx.send(f"🔁 Loop {'ON' if self.loop else 'OFF'}")

    @commands.command()
    async def vol(self, ctx, value: int):
        if value < 1 or value > 100:
            return await ctx.send("❌ Volume 1-100 ke beech")
        self.volume = value / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = self.volume
        await ctx.send(f"🔊 Volume set to {value}%")

async def setup(bot):
    await bot.add_cog(Music(bot))
