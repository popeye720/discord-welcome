import discord
from discord.ext import commands
import wavelink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import asyncio

# ================= SPOTIFY SETUP =================

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    )
)

# ================= MUSIC CONTROLS =================

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="Pause", emoji="⏸️")
    async def pause(self, interaction, button):
        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, interaction, button):
        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️")
    async def skip(self, interaction, button):
        await self.player.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️")
    async def stop(self, interaction, button):
        await self.player.disconnect()
        await interaction.response.send_message("⏹️ Stopped & left VC", ephemeral=True)
        self.stop()

# ================= MUSIC COG =================

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Pehle VC join karo")
            return False
        return True

    def spotify_to_query(self, text: str) -> str | None:
        try:
            if "open.spotify.com/track" in text:
                track = sp.track(text)
            else:
                result = sp.search(q=text, type="track", limit=1)
                if not result["tracks"]["items"]:
                    return None
                track = result["tracks"]["items"][0]

            name = track["name"]
            artist = track["artists"][0]["name"]
            return f"{name} {artist}"
        except:
            return None

    # ---------------- PLAY ----------------
    @commands.command()
    async def play(self, ctx, *, query: str):

        if not await self.ensure_voice(ctx):
            return

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        # 🎧 Spotify → text
        search_query = self.spotify_to_query(query)
        if not search_query:
            await ctx.send("❌ Spotify par song nahi mila")
            await asyncio.sleep(3)
            await player.disconnect()
            return

        # 🔊 SoundCloud fallback
        tracks = await wavelink.Playable.search(f"scsearch:{search_query}")
        if not tracks:
            await ctx.send("❌ Spotify song SoundCloud par available nahi hai")
            await asyncio.sleep(3)
            await player.disconnect()
            return

        track = tracks[0]

        if player.playing:
            player.queue.put(track)
            await ctx.send(f"📥 Queued: **{track.title}**")
        else:
            await player.play(track)
            await ctx.send(
                f"🎶 Now Playing: **{track.title}**",
                view=MusicControls(player)
            )

    # ---------------- QUEUE ----------------
    @commands.command()
    async def queue(self, ctx):
        player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.send("📭 Queue empty")

        desc = "\n".join(
            f"{i+1}. {t.title}" for i, t in enumerate(player.queue)
        )

        await ctx.send(
            embed=discord.Embed(
                title="📜 Queue",
                description=desc,
                color=discord.Color.green()
            )
        )

    # ---------------- SKIP ----------------
    @commands.command()
    async def skip(self, ctx):
        player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Kuch play nahi ho raha")

        await player.stop()
        await ctx.send("⏭️ Skipped")

    # ---------------- STOP ----------------
    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("⏹️ Stopped & left VC")

    # ---------------- AUTO NEXT / AUTO LEAVE ----------------
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player

        if not player.queue.is_empty:
            await player.play(player.queue.get())
        else:
            await asyncio.sleep(10)
            if not player.playing:
                await player.disconnect()

async def setup(bot):
    await bot.add_cog(Music(bot))
