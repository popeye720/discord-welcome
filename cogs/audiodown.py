import discord
from discord.ext import commands
from discord import Embed
import yt_dlp
import asyncio
import os
from database.models import audiodown_col  

class AudioDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.download_lock = asyncio.Lock()  # Only one download at a time

    # -------- ADMIN / OWNER CHECK --------
    def is_admin():
        async def predicate(ctx):
            return ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id
        return commands.check(predicate)

    # -------- SETUP AUDIO DOWNLOADER --------
    @commands.command(name="audiodownsetup")
    @is_admin()
    async def audiodownsetup(self, ctx, channel: discord.TextChannel):
        guild = ctx.guild
        data = audiodown_col.find_one({"guild_id": guild.id})

        if data and data.get("enabled"):
            return await ctx.reply("⚠️ Audio downloader already set up.")

        # Send embed instructions
        embed = Embed(
            title="🎵 YouTube Audio Downloader",
            description=f"To download audio, use the command:\n`!audiodown <YouTube URL>`\n\n**Only works in this channel!**",
            color=discord.Color.green()
        )
        msg = await channel.send(embed=embed)

        # Save setup in DB
        audiodown_col.update_one(
            {"guild_id": guild.id},
            {"$set": {"channel_id": channel.id, "setup_msg_id": msg.id, "enabled": True}},
            upsert=True
        )

        await ctx.reply(f"✅ Audio downloader setup complete in {channel.mention}.")

    # -------- DISABLE AUDIO DOWNLOADER --------
    @commands.command(name="disableaudiodown")
    @is_admin()
    async def disableaudiodown(self, ctx):
        guild = ctx.guild
        data = audiodown_col.find_one({"guild_id": guild.id})
        if not data or not data.get("enabled"):
            return await ctx.reply("⚠️ Audio downloader is not enabled.")

        # Delete setup embed
        channel = guild.get_channel(data["channel_id"])
        try:
            msg = await channel.fetch_message(data["setup_msg_id"])
            await msg.delete()
        except:
            pass

        # Update DB
        audiodown_col.update_one({"guild_id": guild.id}, {"$set": {"enabled": False}})
        await ctx.reply("❌ Audio downloader disabled.")

    # -------- DOWNLOAD AUDIO COMMAND --------
    @commands.command(name="audiodown")
    async def audiodown(self, ctx, url: str):
        guild = ctx.guild
        author = ctx.author
        data = audiodown_col.find_one({"guild_id": guild.id})

        # Check setup & channel
        if not data or not data.get("enabled"):
            return await ctx.reply("⚠️ Audio downloader is not set up.")

        if ctx.channel.id != data["channel_id"]:
            # Admin/Owner bypass
            if not (author.guild_permissions.administrator or author.id == guild.owner_id):
                warning = await ctx.channel.send(f"⚠️ Use this command only in <#{data['channel_id']}>")
                await asyncio.sleep(2)
                await ctx.message.delete()
                await warning.delete()
                return

        # Lock for one download at a time
        if self.download_lock.locked():
            return await ctx.reply("⏳ Another download is in progress. Please wait.")

        async with self.download_lock:
            msg = await ctx.reply(f"⬇️ Downloading audio for {url} ...")
            temp_file = f"temp_{ctx.guild.id}_{ctx.author.id}.webm"

            # yt-dlp options (no FFmpeg, direct webm)
            ydl_opts = {
                "format": "bestaudio[ext=webm]/bestaudio",
                "outtmpl": temp_file,
                "noplaylist": True,
                "quiet": True,
                "simulate": True
            }

            try:
                # Fetch info first to check size
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    filesize = info.get("filesize") or info.get("filesize_approx") or 0
                    if filesize > 7 * 1024 * 1024:  # >7MB
                        return await msg.edit(content="❌ Audio file exceeds 7 MB, cannot download.")

                # Download audio
                ydl_opts["simulate"] = False
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Final size check (in case info['filesize'] was None)
                if os.path.exists(temp_file):
                    if os.path.getsize(temp_file) > 7 * 1024 * 1024:
                        await msg.edit(content="❌ Audio file exceeds 7 MB after download.")
                        os.remove(temp_file)
                        return
                    await ctx.channel.send(content=f"🎶 {author.mention}", file=discord.File(temp_file))
                    os.remove(temp_file)

                await msg.delete()

            except Exception as e:
                await msg.edit(content=f"❌ Failed to download audio: {str(e)}")

            await asyncio.sleep(30)  # Cooldown time

async def setup(bot):
    await bot.add_cog(AudioDownloader(bot))


