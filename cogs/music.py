# cogs/music.py
import asyncio
import discord
from discord.ext import commands
import yt_dlp
import os

# ===================== CONFIG =====================

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "skip_download": True,
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
    "ignoreerrors": True,
}

FFMPEG_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin"

ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)

def get_ffmpeg_executable():
    # Railway / Linux
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        return env_path

    # Local Windows support (kept for safety)
    if os.path.isfile("./ffmpeg.exe"):
        return "./ffmpeg.exe"

    return "ffmpeg"

FFMPEG_EXEC = get_ffmpeg_executable()

# ===================== SONG =====================

class Song:
    def __init__(self, info, requested_by=None, text_channel=None):
        self.title = info.get("title", "Unknown")
        self.webpage_url = info.get("webpage_url")
        self.requested_by = requested_by
        self.text_channel = text_channel

        self.stream_url = info.get("url")

        # fallback if direct url missing
        if not self.stream_url:
            for f in reversed(info.get("formats", [])):
                if f.get("acodec") != "none":
                    self.stream_url = f.get("url")
                    break

# ===================== CONTROL PANEL =====================

class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = str(guild_id)

    def get_vc(self):
        data = self.cog.guild_data.get(self.guild_id)
        return data.get("player") if data else None

    @discord.ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_vc()
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Paused.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_vc()
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_vc()
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("Skipped.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⛔", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self.cog.guild_data.get(self.guild_id)
        vc = self.get_vc()

        if data:
            data["queue"].clear()
            data["playing"] = False

        if vc:
            await vc.disconnect()

        await interaction.response.send_message(
            "Music stopped and queue cleared.",
            ephemeral=True
        )

# ===================== MUSIC COG =====================

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_data = {}

    def ensure_guild(self, guild_id):
        gid = str(guild_id)
        if gid not in self.guild_data:
            self.guild_data[gid] = {
                "queue": [],
                "player": None,
                "playing": False
            }
        return self.guild_data[gid]

    async def play_next(self, guild_id):
        await asyncio.sleep(0.2)
        data = self.guild_data.get(str(guild_id))

        if not data or not data["queue"]:
            data["playing"] = False
            return

        song = data["queue"].pop(0)
        vc = data["player"]

        if not vc or not vc.is_connected():
            data["playing"] = False
            return

        source = discord.FFmpegPCMAudio(
            song.stream_url,
            executable=FFMPEG_EXEC,
            before_options=FFMPEG_OPTIONS
        )

        def after_play(err):
            asyncio.run_coroutine_threadsafe(
                self.play_next(guild_id),
                self.bot.loop
            )

        vc.play(source, after=after_play)
        data["playing"] = True

        if song.text_channel:
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"**{song.title}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested by {song.requested_by}")
            await song.text_channel.send(
                embed=embed,
                view=MusicControlView(self, guild_id)
            )

    # ===================== COMMANDS =====================

    @commands.command(name="play")
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Voice channel join karo pehle.")

        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect()

        data = self.ensure_guild(ctx.guild.id)
        data["player"] = vc

        msg = await ctx.send("🔍 Searching...")
        info = await asyncio.to_thread(ytdl.extract_info, query, False)

        if not info:
            return await msg.edit(content="❌ Song nahi mila.")

        if "entries" in info:
            info = info["entries"][0]

        song = Song(info, ctx.author, ctx.channel)
        data["queue"].append(song)

        await msg.edit(content=f"✅ Queued: **{song.title}**")

        if not data["playing"]:
            await self.play_next(ctx.guild.id)

    @commands.command(name="queue")
    async def queue(self, ctx):
        data = self.guild_data.get(str(ctx.guild.id))
        if not data or not data["queue"]:
            return await ctx.send("📭 Queue empty hai.")

        text = "\n".join(
            f"{i+1}. {s.title}" for i, s in enumerate(data["queue"][:10])
        )
        await ctx.send("🎶 **Queue:**\n" + text)

# ===================== SETUP =====================

async def setup(bot):
    await bot.add_cog(Music(bot))
