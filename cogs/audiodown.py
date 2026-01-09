import discord
from discord.ext import commands
from discord import app_commands, Embed
import yt_dlp
import asyncio
import os
from database.models import audiodown_col  

class AudioDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.download_lock = asyncio.Lock()

    # -------- ADMIN CHECK --------
    def is_admin():
        async def predicate(interaction: discord.Interaction):
            guild = interaction.guild
            if guild is None:
                return False
            return interaction.user.guild_permissions.administrator or interaction.user.id == guild.owner_id
        return app_commands.check(predicate)

    # -------- SETUP --------
    @app_commands.command(name="audiodownsetup", description="Setup the audio downloader channel")
    @is_admin()
    async def audiodownsetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild = interaction.guild
        data = audiodown_col.find_one({"guild_id": guild.id})

        if data and data.get("enabled"):
            return await interaction.response.send_message("⚠️ Audio downloader already set up.", ephemeral=True)

        embed = Embed(
            title="🎵 YouTube Audio Downloader",
            description=f"Use `/audiodown <YouTube URL>` to download audio in this channel.",
            color=discord.Color.green()
        )
        msg = await channel.send(embed=embed)

        audiodown_col.update_one(
            {"guild_id": guild.id},
            {"$set": {"channel_id": channel.id, "setup_msg_id": msg.id, "enabled": True}},
            upsert=True
        )

        await interaction.response.send_message(f"✅ Setup complete in {channel.mention}", ephemeral=True)

    # -------- DISABLE --------
    @app_commands.command(name="disableaudiodown", description="Disable audio downloader")
    @is_admin()
    async def disableaudiodown(self, interaction: discord.Interaction):
        guild = interaction.guild
        data = audiodown_col.find_one({"guild_id": guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message("⚠️ Not enabled.", ephemeral=True)

        channel = guild.get_channel(data["channel_id"])
        try:
            msg = await channel.fetch_message(data["setup_msg_id"])
            await msg.delete()
        except:
            pass

        audiodown_col.update_one({"guild_id": guild.id}, {"$set": {"enabled": False}})
        await interaction.response.send_message("❌ Audio downloader disabled.", ephemeral=True)

    # -------- DOWNLOAD AUDIO --------
    @app_commands.command(name="audiodown", description="Download audio from YouTube")
    @app_commands.default_permissions(send_messages=True)
    async def audiodown(self, interaction: discord.Interaction, url: str):
        guild = interaction.guild
        author = interaction.user
        data = audiodown_col.find_one({"guild_id": guild.id})

        if not data or not data.get("enabled"):
            return await interaction.response.send_message("⚠️ Not set up.", ephemeral=True)

        if interaction.channel.id != data["channel_id"]:
            if not (author.guild_permissions.administrator or author.id == guild.owner_id):
                warning = await interaction.followup.send(f"⚠️ Use <#{data['channel_id']}>", ephemeral=True)
                return

        if self.download_lock.locked():
            return await interaction.response.send_message("⏳ Another download in progress.", ephemeral=True)

        async with self.download_lock:
            await interaction.response.send_message(f"⬇️ Downloading {url} ...", ephemeral=True)
            temp_file = f"temp_{guild.id}_{author.id}.webm"

            ydl_opts = {
                "format": "bestaudio[ext=webm]/bestaudio",
                "outtmpl": temp_file,
                "noplaylist": True,
                "quiet": True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    filesize = info.get("filesize") or info.get("filesize_approx") or 0
                    if filesize > 7*1024*1024:
                        return await interaction.edit_original_response(content="❌ File exceeds 7MB.")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if os.path.exists(temp_file):
                    await interaction.channel.send(file=discord.File(temp_file))
                    os.remove(temp_file)

                await interaction.delete_original_response()

            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Failed: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AudioDownloader(bot))
