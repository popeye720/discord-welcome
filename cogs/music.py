import discord
from discord.ext import commands
import wavelink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import asyncio

# ================= ENV =================

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BLOCKED_CHANNEL_MUSIC = int(os.getenv("BLOCKED_CHANNEL_MUSIC", "0"))

# ================= SPOTIFY SETUP =================

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    )
)

# ================= BUTTON LOCK CHECK =================

def is_locked(interaction: discord.Interaction) -> bool:
    bot = interaction.client
    return getattr(bot, "owner_locked", False) and interaction.user.id != OWNER_ID

# ================= MUSIC CONTROLS =================

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

        if not hasattr(self.player, "loop"):
            self.player.loop = False

    @discord.ui.button(label="Pause", emoji="⏸️")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):

        if is_locked(interaction):
            return await interaction.response.send_message(
                "🚫 Music is locked by OWNER.",
                ephemeral=True
            )

        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):

        if is_locked(interaction):
            return await interaction.response.send_message(
                "🚫 Music is locked by OWNER.",
                ephemeral=True
            )

        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):

        if is_locked(interaction):
            return await interaction.response.send_message(
                "🚫 Music is locked by OWNER.",
                ephemeral=True
            )

        await self.player.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(label="Loop", emoji="🔁")
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):

        if is_locked(interaction):
            return await interaction.response.send_message(
                "🚫 Music is locked by OWNER.",
                ephemeral=True
            )

        self.player.loop = not self.player.loop
        status = "ON 🔁" if self.player.loop else "OFF ❌"

        await interaction.response.send_message(
            f"🔁 Loop is now **{status}**",
            ephemeral=True
        )

    @discord.ui.button(label="Stop", emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):

        if is_locked(interaction):
            return await interaction.response.send_message(
                "🚫 Music is locked by OWNER.",
                ephemeral=True
            )

        self.player.loop = False
        await self.player.disconnect()
        await interaction.response.send_message(
            "⏹️ Stopped & left VC",
            ephemeral=True
        )
        self.stop()

# ================= MUSIC COG =================

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Please join a voice channel first.")
            return False
        return True

    async def temp_block_reply(self, ctx, text: str, delay: int = 3):
        try:
            bot_msg = await ctx.send(text)
            await asyncio.sleep(delay)
            await ctx.message.delete()
            await bot_msg.delete()
        except:
            pass

    def is_blocked_channel(self, ctx) -> bool:
        if ctx.author.id == OWNER_ID:
            return False

        if not ctx.author.voice or not ctx.author.voice.channel:
            return False

        blocked_vc = getattr(self.bot, "blocked_voice_channel_id", None)
        if blocked_vc and ctx.author.voice.channel.id == blocked_vc:
            return True

        return ctx.author.voice.channel.id == BLOCKED_CHANNEL_MUSIC

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

    def is_owner_locked(self, user_id: int) -> bool:
        return getattr(self.bot, "owner_locked", False) and user_id != OWNER_ID

    @commands.command()
    async def play(self, ctx, *, query: str):

        if self.is_owner_locked(ctx.author.id):
            return await self.temp_block_reply(
                ctx, "🚫 Bot is currently locked by the owner."
            )

        if not await self.ensure_voice(ctx):
            return

        if self.is_blocked_channel(ctx):
            return await ctx.send("🚫 Music playback is disabled in this VC.")

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        search_queries = self.spotify_to_queries(query)

        if not search_queries:
            await ctx.send("❌ No song found on Spotify.")
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
                await ctx.send(
                    f"🎶 Now Playing: **{track.title}**",
                    view=MusicControls(player)
                )

        if len(search_queries) > 1:
            await ctx.send(f"📥 Added **{len(search_queries)}** tracks to queue.")

    @commands.command()
    async def skip(self, ctx):

        if self.is_owner_locked(ctx.author.id):
            return await self.temp_block_reply(
                ctx, "🚫 Bot is currently locked by the owner."
            )

        player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Nothing is playing.")

        await player.stop()
        await ctx.send("⏭️ Skipped.")

    @commands.command()
    async def stop(self, ctx):

        if self.is_owner_locked(ctx.author.id):
            return await self.temp_block_reply(
                ctx, "🚫 Bot is currently locked by the owner."
            )

        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("⏹️ Stopped & left VC.")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player

        if getattr(player, "loop", False):
            await player.play(payload.track)
            return

        if not player.queue.is_empty:
            await player.play(player.queue.get())
        else:
            await asyncio.sleep(10)
            if not player.playing:
                await player.disconnect()

async def setup(bot):
    await bot.add_cog(Music(bot))
