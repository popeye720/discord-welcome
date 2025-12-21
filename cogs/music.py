import discord
from discord.ext import commands
from discord import app_commands
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
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        await interaction.response.send_message("⏹️ Stopped & left VC", ephemeral=True)
        self.stop()

# ================= MUSIC COG =================

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ Please join a voice channel first.",
                ephemeral=True
            )
            return False
        return True

    # ---------- SPOTIFY PARSER ----------
    def spotify_to_queries(self, query: str) -> list[str]:
        results = []
        try:
            if "open.spotify.com/track" in query:
                track = sp.track(query)
                results.append(f"{track['name']} {track['artists'][0]['name']}")

            elif "open.spotify.com/playlist" in query:
                playlist = sp.playlist_items(query)
                for item in playlist["items"]:
                    track = item["track"]
                    if track:
                        results.append(f"{track['name']} {track['artists'][0]['name']}")

            else:
                search = sp.search(q=query, type="track", limit=1)
                if search["tracks"]["items"]:
                    track = search["tracks"]["items"][0]
                    results.append(f"{track['name']} {track['artists'][0]['name']}")

        except Exception:
            return []

        return results

    # ---------------- PLAY ----------------
    @app_commands.command(name="play", description="Play music from Spotify or search")
    async def play(self, interaction: discord.Interaction, query: str):

        if not await self.ensure_voice(interaction):
            return

        await interaction.response.defer()

        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)

        search_queries = self.spotify_to_queries(query)

        if not search_queries:
            await interaction.followup.send("❌ No song found on Spotify.")
            await asyncio.sleep(3)
            await player.disconnect()
            return

        for search in search_queries:
            tracks = await wavelink.Playable.search(search)
            if not tracks:
                continue

            track = tracks[0]

            if player.playing or not player.queue.is_empty:
                player.queue.put(track)
            else:
                await player.play(track)
                await interaction.followup.send(
                    f"🎶 Now Playing: **{track.title}**",
                    view=MusicControls(player)
                )

        if len(search_queries) > 1:
            await interaction.followup.send(
                f"📥 Added **{len(search_queries)}** tracks to queue."
            )

    # ---------------- QUEUE ----------------
    @app_commands.command(name="queue", description="Show music queue")
    async def queue(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            return await interaction.response.send_message(
                "📭 Queue is empty.",
                ephemeral=True
            )

        desc = "\n".join(
            f"{i+1}. {t.title}" for i, t in enumerate(player.queue)
        )

        await interaction.response.send_message(
            embed=discord.Embed(
                title="📜 Queue",
                description=desc,
                color=discord.Color.green()
            )
        )

    # ---------------- SKIP ----------------
    @app_commands.command(name="skip", description="Skip current track")
    async def skip(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message(
                "❌ Nothing is playing.",
                ephemeral=True
            )

        await player.stop()
        await interaction.response.send_message("⏭️ Skipped.")

    # ---------------- STOP ----------------
    @app_commands.command(name="stop", description="Stop music and leave VC")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message(
                "⏹️ Stopped & left voice channel."
            )

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
    await bot.tree.sync()
