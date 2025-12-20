import discord
from discord.ext import commands
import wavelink

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Pehle voice channel join karo")
            return False
        return True

    # ▶️ PLAY
    @commands.command()
    async def play(self, ctx, *, search: str):
        if not await self.ensure_voice(ctx):
            return

        player: wavelink.Player = ctx.voice_client

        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send("❌ No results found")

        track = tracks[0]
        await player.play(track)

        await ctx.send(f"▶️ **Playing:** {track.title}")

    # ⏸️ PAUSE
    @commands.command()
    async def pause(self, ctx):
        player = ctx.voice_client
        if player and player.playing:
            await player.pause()
            await ctx.send("⏸️ Paused")

    # ▶️ RESUME
    @commands.command()
    async def resume(self, ctx):
        player = ctx.voice_client
        if player and player.paused:
            await player.resume()
            await ctx.send("▶️ Resumed")

    # ⏭️ SKIP
    @commands.command()
    async def skip(self, ctx):
        player = ctx.voice_client
        if player:
            await player.stop()
            await ctx.send("⏭️ Skipped")

    # ⏹️ STOP
    @commands.command()
    async def stop(self, ctx):
        player = ctx.voice_client
        if player:
            await player.disconnect()
            await ctx.send("⏹️ Stopped & left")

async def setup(bot):
    await bot.add_cog(Music(bot))
