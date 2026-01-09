import discord
from discord.ext import commands
from discord import app_commands, Embed
import yt_dlp
import asyncio
import os
from database.models import audiodown_col  

class AudioDownloader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.download_lock = asyncio.Lock()  # Only one download at a time

    # -------- ADMIN / OWNER CHECK (SAME LOGIC) --------
    async def is_admin(self, interaction: discord.Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or interaction.user.id == interaction.guild.owner_id
        )

    # -------- SETUP AUDIO DOWNLOADER --------
    @app_commands.command(name="audiodownsetup", description="Setup audio downloader")
    async def audiodownsetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
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
            description=(
                "To download audio, use:\n"
                "`/audiodown <YouTube URL>`\n\n"
                "**Only works in this channel!**"
            ),
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
            f"✅ Audio downloader setup complete in {channel.mention}.",
            ephemeral=True
        )

    # -------- DISABLE AUDIO DOWNLOADER --------
    @app_commands.command(name="disableaudiodown", description="Disable audio downloader")
    async def disableaudiodown(self, interaction: discord.Interaction):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                "❌ Only admins or owner can use this.",
                ephemeral=True
            )

        guild = interaction.guild
        data = audiodown_col.find_one({"guild_id": guild.id})

        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Audio downloader is not enabled.",
                ephemeral=True
            )

        channel = guild.get_channel(data["channel_id"])
        try:
            msg = await channel.fetch_message(data["setup_msg_id"])
            await msg.delete()
        except:
            pass

        audiodown_col.update_one(
            {"guild_id": guild.id},
            {"$set": {"enabled": False}}
        )

        await interaction.response.send_message(
            "❌ Audio downloader disabled.",
            ephemeral=True
        )

    # -------- DOWNLOAD AUDIO --------
    @app_commands.command(name="audiodown", description="Download YouTube audio")
    @app_commands.default_permissions(send_messages=True)
    async def audiodown(self, interaction: discord.Interaction, url: str):
        guild = interaction.guild
        author = interaction.user
        data = audiodown_col.find_one({"guild_id": guild.id})

        # Check setup
        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Audio downloader is not set up.",
                ephemeral=True
            )

        # Channel restriction (SAME AS ! LOGIC)
        if interaction.channel.id != data["channel_id"]:
            if not (
                author.guild_permissions.administrator
                or author.id == guild.owner_id
            ):
                warning = await interaction.channel.send(
                    f"⚠️ Use this command only in <#{data['channel_id']}>"
                )
                await asyncio.sleep(2)
                await warning.delete()
                return await interaction.response.send_message(
                    "⚠️ Wrong channel.",
                    ephemeral=True
                )

        # Lock check
        if self.download_lock.locked():
            return await interaction.response.send_message(
                "⏳ Another download is in progress. Please wait.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"⬇️ Downloading audio for {url} ...",
            ephemeral=True
        )

        async with self.download_lock:
            temp_file = f"temp_{guild.id}_{author.id}.webm"

            ydl_opts = {
                "format": "bestaudio[ext=webm]/bestaudio",
                "outtmpl": temp_file,
                "noplaylist": True,
                "quiet": True,
                "simulate": True
            }

            try:
                # Size check BEFORE download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    filesize = info.get("filesize") or info.get("filesize_approx") or 0
                    if filesize > 7 * 1024 * 1024:
                        return await interaction.edit_original_response(
                            content="❌ Audio file exceeds 7 MB, cannot download."
                        )

                # Download
                ydl_opts["simulate"] = False
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Final size check
                if os.path.exists(temp_file):
                    if os.path.getsize(temp_file) > 7 * 1024 * 1024:
                        os.remove(temp_file)
                        return await interaction.edit_original_response(
                            content="❌ Audio file exceeds 7 MB after download."
                        )

                    await interaction.channel.send(
                        content=f"🎶 {author.mention}",
                        file=discord.File(temp_file)
                    )
                    os.remove(temp_file)

                await interaction.delete_original_response()

            except Exception as e:
                await interaction.edit_original_response(
                    content=f"❌ Failed to download audio: {e}"
                )

            await asyncio.sleep(30)  # SAME cooldown

# ---------------- COG SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(AudioDownloader(bot))
