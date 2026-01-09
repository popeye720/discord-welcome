import discord
from discord.ext import commands
from discord import Embed
import yt_dlp
import asyncio
import contextlib
import os

from database.models import audiodown_col

MAX_SIZE = 7 * 1024 * 1024  # 7 MB


class AudioDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.download_locks = {}

    async def get_guild_lock(self, guild_id: str):
        if guild_id not in self.download_locks:
            self.download_locks[guild_id] = asyncio.Lock()
        return self.download_locks[guild_id]

    # -------- PERMISSION CHECK (ADMIN / OWNER) --------
    @staticmethod
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SETUP COMMAND --------
    @commands.command(name="audiodownsetup")
    @is_admin()
    async def audiodownsetup(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        existing = audiodown_col.find_one({"guild_id": guild_id})
        if existing:
            return await ctx.reply("⚠️ Audio downloader already set up.")

        embed = Embed(
            title="🎵 YouTube Audio Downloader",
            description="Use `!audiodown <YouTube URL>` in this channel.",
            color=discord.Color.green()
        )
        msg = await channel.send(embed=embed)

        audiodown_col.insert_one({
            "guild_id": guild_id,
            "channel_id": channel.id,
            "setup_msg_id": msg.id,
            "enabled": True
        })

        await ctx.reply(f"✅ Setup complete in {channel.mention}")

    # -------- DOWNLOAD COMMAND --------
    @commands.command(name="audiodown")
    async def audiodown(self, ctx, url: str):
        guild_id = ctx.guild.id
        data = audiodown_col.find_one({"guild_id": guild_id})
        if not data or not data.get("enabled"):
            return await ctx.reply("⚠️ Audio downloader is not set up.")

        if ctx.channel.id != data["channel_id"]:
            if not (ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id):
                warn = await ctx.channel.send(f"⚠️ Use <#{data['channel_id']}>")
                await asyncio.sleep(2)
                await ctx.message.delete()
                await warn.delete()
                return

        lock = await self.get_guild_lock(guild_id)
        if lock.locked():
            return await ctx.reply("⏳ Another download is already in progress.")

        async with lock:
            status = await ctx.reply(
                f"🔍 **Checking audio size for {ctx.author.mention}**\n"
                f"⏳ Please wait… do not delete this message"
            )

            info_opts = {
                "format": "bestaudio",
                "quiet": True,
                "noplaylist": True,
                "no_warnings": True,
                "logger": None
            }

            try:
                downloaded_file = None
                with open(os.devnull, "w") as fnull:
                    with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
                        with yt_dlp.YoutubeDL(info_opts) as ydl:
                            info = ydl.extract_info(url, download=False)

                filesize = (
                    info.get("filesize")
                    or info.get("filesize_approx")
                    or info.get("filesize_estimate")
                )

                if info.get("is_live"):
                    return await status.edit(
                        content=f"⚠️ {ctx.author.mention}, live streams cannot be downloaded."
                    )

                if filesize and filesize > MAX_SIZE:
                    return await status.edit(
                        content=(f"❌ **File too large**\n"
                                 f"Estimated size: `{filesize / 1024 / 1024:.2f} MB`\n"
                                 f"Discord limit is **7 MB**")
                    )

                await status.edit(
                    content=f"⬇️ **Downloading audio for {ctx.author.mention}**\n⏳ Please wait…"
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
                        try:
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(url, download=True)
                                downloaded_file = ydl.prepare_filename(info)
                        except yt_dlp.utils.DownloadError as de:
                            if "Requested format is not available" in str(de):
                                return await status.edit(
                                    content=f"⚠️ {ctx.author.mention}, live streams cannot be downloaded."
                                )
                            else:
                                raise de

                if not downloaded_file or not os.path.exists(downloaded_file):
                    return await status.edit(content="❌ Download failed.")

                file_size = os.path.getsize(downloaded_file)
                if file_size > MAX_SIZE:
                    os.remove(downloaded_file)
                    return await status.edit(
                        content="❌ File exceeded **7 MB** after download."
                    )

                await status.edit(content="📤 Uploading audio to Discord…")

                await ctx.channel.send(
                    content=f"✅ **Done!** {ctx.author.mention}, your audio is ready 👇",
                    file=discord.File(downloaded_file)
                )

                os.remove(downloaded_file)

                await status.edit(
                    content=f"✅ **Completed successfully** for {ctx.author.mention}"
                )

            except Exception as e:
                await status.edit(content=f"❌ Failed: `{e}`")

    # -------- DISABLE COMMAND --------
    @commands.command(name="audiodowndisable")
    @is_admin()
    async def audiodowndisable(self, ctx):
        guild_id = ctx.guild.id
        data = audiodown_col.find_one({"guild_id": guild_id})
        if not data or not data.get("enabled"):
            return await ctx.reply("⚠️ Audio downloader is not set up.")

        audiodown_col.find_one_and_delete({"guild_id": guild_id})
        await ctx.reply(f"✅ Audio downloader disabled for **{ctx.guild.name}**.")


# -------- SETUP COG FOR EXTENSION LOADING --------
async def setup(bot):
    await bot.add_cog(AudioDownloader(bot))
