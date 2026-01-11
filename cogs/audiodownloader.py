import discord
from discord.ext import commands
from discord import app_commands, Embed
import yt_dlp
import asyncio
import os
import contextlib

from database.models import audiodown_col

MAX_SIZE = 7 * 1024 * 1024  # 7 MB

class AudioDownloader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.download_locks: dict[int, asyncio.Lock] = {}

    # -------------------------------
    # PER GUILD LOCK
    # -------------------------------
    async def get_guild_lock(self, guild_id: int):
        if guild_id not in self.download_locks:
            self.download_locks[guild_id] = asyncio.Lock()
        return self.download_locks[guild_id]

    # -------------------------------
    # ADMIN CHECK
    # -------------------------------
    async def is_admin(self, interaction: discord.Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or interaction.user.id == interaction.guild.owner_id
        )

    # -------------------------------
    # SETUP COMMAND
    # -------------------------------
    @app_commands.command(name="audiodownsetup", description="Setup audio downloader")
    @app_commands.describe(channel="Text channel where audio downloader works")
    async def audiodownsetup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                "❌ Only admins or owner can use this.",
                ephemeral=True
            )

        guild = interaction.guild
        data = audiodown_col.find_one({"guild_id": guild.id})

        if data and data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Audio downloader already set up.",
                ephemeral=True
            )

        embed = Embed(
            title="🎵 YouTube Audio Downloader",
            description="Use `/audiodown <YouTube URL>` in this channel.",
            color=discord.Color.green()
        )

        msg = await channel.send(embed=embed)

        audiodown_col.update_one(
            {"guild_id": guild.id},
            {"$set": {
                "channel_id": channel.id,
                "setup_msg_id": msg.id,
                "enabled": True
            }},
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Setup complete in {channel.mention}",
            ephemeral=True
        )

    # -------------------------------
    # DOWNLOAD COMMAND
    # -------------------------------
    @app_commands.command(name="audiodown", description="Download YouTube audio")
    @app_commands.describe(url="YouTube video URL to download audio from")
    async def audiodown(
        self,
        interaction: discord.Interaction,
        url: str
    ):
        guild = interaction.guild
        author = interaction.user

        data = audiodown_col.find_one({"guild_id": guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Audio downloader is not set up.",
                ephemeral=True
            )

        # Channel restriction
        if interaction.channel.id != data["channel_id"]:
            if not await self.is_admin(interaction):
                warn = await interaction.channel.send(
                    f"⚠️ Use <#{data['channel_id']}>"
                )
                await asyncio.sleep(2)
                await warn.delete()
                return await interaction.response.send_message(
                    "⚠️ Wrong channel.",
                    ephemeral=True
                )

        lock = await self.get_guild_lock(guild.id)
        if lock.locked():
            return await interaction.response.send_message(
                "⏳ Another download is already in progress.",
                ephemeral=True
            )

        # INITIAL STATUS MESSAGE
        await interaction.response.send_message(
            f"🔍 **Checking audio size for {author.mention}**\n"
            "⏳ Please wait… do not delete this message"
        )
        status_msg = await interaction.original_response()

        async with lock:
            downloaded_file = None
            try:
                # ---------- SIZE CHECK BEFORE DOWNLOAD ----------
                info_opts = {
                    "format": "bestaudio",
                    "quiet": True,
                    "noplaylist": True,
                    "no_warnings": True,
                    "logger": None
                }

                with open(os.devnull, "w") as fnull, contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
                    with yt_dlp.YoutubeDL(info_opts) as ydl:
                        info = ydl.extract_info(url, download=False)

                if info.get("is_live"):
                    return await status_msg.edit(
                        content=f"⚠️ {author.mention}, live streams cannot be downloaded."
                    )

                filesize = (
                    info.get("filesize")
                    or info.get("filesize_approx")
                    or info.get("filesize_estimate")
                )

                if filesize and filesize > MAX_SIZE:
                    return await status_msg.edit(
                        content=(
                            "❌ **File too large**\n"
                            f"Estimated size: `{filesize / 1024 / 1024:.2f} MB`\n"
                            "Discord limit is **7 MB**"
                        )
                    )

                # ---------- DOWNLOADING ----------
                await status_msg.edit(
                    content=f"⬇️ **Downloading audio for {author.mention}**\n⏳ Please wait…"
                )

                ydl_opts = {
                    "format": "bestaudio[ext=webm]/bestaudio",
                    "outtmpl": "%(title)s.%(ext)s",
                    "quiet": True,
                    "noplaylist": True,
                    "restrictfilenames": True,
                    "no_warnings": True,
                    "logger": None
                }

                with open(os.devnull, "w") as fnull, contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        downloaded_file = ydl.prepare_filename(info)

                if not downloaded_file or not os.path.exists(downloaded_file):
                    return await status_msg.edit(content="❌ Download failed.")

                # ---------- FINAL SIZE CHECK ----------
                if os.path.getsize(downloaded_file) > MAX_SIZE:
                    os.remove(downloaded_file)
                    return await status_msg.edit(
                        content="❌ File exceeded **7 MB** after download."
                    )

                # ---------- UPLOAD ----------
                await status_msg.edit(content="📤 Uploading audio to Discord…")

                await interaction.channel.send(
                    content=f"✅ **Done!** {author.mention}, your audio is ready 👇",
                    file=discord.File(downloaded_file)
                )

                os.remove(downloaded_file)

                await status_msg.edit(
                    content=f"✅ **Completed successfully** for {author.mention}"
                )

            except Exception as e:
                if downloaded_file and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)
                await status_msg.edit(content=f"❌ Failed: `{e}`")

    # -------------------------------
    # DISABLE COMMAND
    # -------------------------------
    @app_commands.command(name="disableaudiodown", description="Disable audio downloader")
    async def disableaudiodown(self, interaction: discord.Interaction):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                "❌ Only admins or owner can use this.",
                ephemeral=True
            )

        data = audiodown_col.find_one({"guild_id": interaction.guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Audio downloader is not enabled.",
                ephemeral=True
            )

        audiodown_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": False}}
        )

        await interaction.response.send_message(
            "✅ Audio downloader disabled.",
            ephemeral=True
        )


# ---------- COG SETUP ----------
async def setup(bot: commands.Bot):
    await bot.add_cog(AudioDownloader(bot))
