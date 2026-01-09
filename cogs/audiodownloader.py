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

    # ---------- PER GUILD LOCK ----------
    async def get_guild_lock(self, guild_id: int):
        if guild_id not in self.download_locks:
            self.download_locks[guild_id] = asyncio.Lock()
        return self.download_locks[guild_id]

    # ---------- ADMIN CHECK ----------
    async def is_admin(self, interaction: discord.Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or interaction.user.id == interaction.guild.owner_id
        )

    # ---------- SETUP ----------
    @app_commands.command(name="audiodownsetup", description="Setup audio downloader")
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

    # ---------- DOWNLOAD ----------
    @app_commands.command(name="audiodown", description="Download YouTube audio")
    async def audiodown(self, interaction: discord.Interaction, url: str):
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

        # STATUS MESSAGE
        await interaction.response.send_message(
            embed=Embed(
                title="🔍 Checking audio",
                description=f"Checking audio size for {author.mention}\n⏳ Please wait…",
                color=discord.Color.blurple()
            )
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

                with open(os.devnull, "w") as fnull:
                    with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
                        with yt_dlp.YoutubeDL(info_opts) as ydl:
                            info = ydl.extract_info(url, download=False)

                if info.get("is_live"):
                    return await status_msg.edit(
                        embed=Embed(
                            title="⚠️ Not Supported",
                            description="Live streams cannot be downloaded.",
                            color=discord.Color.orange()
                        )
                    )

                filesize = (
                    info.get("filesize")
                    or info.get("filesize_approx")
                    or info.get("filesize_estimate")
                )

                if filesize and filesize > MAX_SIZE:
                    return await status_msg.edit(
                        embed=Embed(
                            title="❌ File Too Large",
                            description=(
                                f"Estimated size: `{filesize / 1024 / 1024:.2f} MB`\n"
                                "Discord limit is **7 MB**"
                            ),
                            color=discord.Color.red()
                        )
                    )

                # ---------- DOWNLOADING ----------
                await status_msg.edit(
                    embed=Embed(
                        title="⬇️ Downloading",
                        description=f"Downloading audio for {author.mention}",
                        color=discord.Color.blurple()
                    )
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

                with open(os.devnull, "w") as fnull:
                    with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                            downloaded_file = ydl.prepare_filename(info)

                if not downloaded_file or not os.path.exists(downloaded_file):
                    return await status_msg.edit(
                        embed=Embed(
                            title="❌ Failed",
                            description="Download failed.",
                            color=discord.Color.red()
                        )
                    )

                # ---------- FINAL SIZE CHECK ----------
                if os.path.getsize(downloaded_file) > MAX_SIZE:
                    os.remove(downloaded_file)
                    return await status_msg.edit(
                        embed=Embed(
                            title="❌ File Too Large",
                            description="File exceeded **7 MB** after download.",
                            color=discord.Color.red()
                        )
                    )

                # ---------- FINAL SEND (SINGLE MESSAGE) ----------
                final_embed = Embed(
                    title="✅ Download Completed",
                    description=f"{author.mention}, your audio is ready 👇",
                    color=discord.Color.green()
                )

                await status_msg.delete()

                await interaction.channel.send(
                    embed=final_embed,
                    file=discord.File(downloaded_file)
                )

                os.remove(downloaded_file)

            except Exception as e:
                if downloaded_file and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)
                await status_msg.edit(
                    embed=Embed(
                        title="❌ Error",
                        description=str(e),
                        color=discord.Color.red()
                    )
                )

    # ---------- DISABLE ----------
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
