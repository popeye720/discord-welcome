import discord
import time
import asyncio
import os
from discord.ext import commands
from database.models import audiodown_col
import yt_dlp


class Mp3Downloader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- PERMISSION ----------
    def is_owner(self, ctx):
        return ctx.author.id == ctx.guild.owner_id

    def is_admin(self, ctx):
        return ctx.author.guild_permissions.administrator

    # ---------- SETUP ----------
    @commands.command(name="setupdownaudio")
    @commands.guild_only()
    async def setup_downaudio(self, ctx, channel_id: int):
        if not self.is_owner(ctx) and not self.is_admin(ctx):
            return await ctx.reply("❌ Only **Owner or Admin** can setup this system.")

        existing = await audiodown_col.find_one({"guild_id": ctx.guild.id})
        if existing:
            return await ctx.reply("⚠ **Audio download system is already setup.**")

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID.")

        embed = discord.Embed(
            title="🎧 Audio Downloader",
            description=(
                "**Command:** `!downaudio <youtube_url>`\n\n"
                "📌 Download audio from a **single YouTube video**\n"
                "🎵 Format: **webm / m4a (original audio)**\n"
                "📏 Max Size: **7 MB**\n"
                "⏳ Cooldown: **30 seconds**\n\n"
                "❌ Playlist links are not allowed\n"
                "⚠ Use this command **only in this channel**"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="TEJAS • Audio Downloader")

        guide_msg = await channel.send(embed=embed)

        await audiodown_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel_id,
            "guide_msg_id": guide_msg.id,
            "last_done": 0
        })

        await ctx.reply(f"✅ Audio download system enabled in {channel.mention}")

    # ---------- DISABLE ----------
    @commands.command(name="disabledownaudio")
    @commands.guild_only()
    async def disable_downaudio(self, ctx):
        if not self.is_owner(ctx) and not self.is_admin(ctx):
            return await ctx.reply("❌ Only **Owner or Admin** can disable this system.")

        config = await audiodown_col.find_one({"guild_id": ctx.guild.id})
        if not config:
            return await ctx.reply("⚠ **Audio download system is not setup.**")

        channel = ctx.guild.get_channel(config["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(config["guide_msg_id"])
                await msg.delete()
            except:
                pass

        await audiodown_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.reply("🗑 **Audio download system fully disabled.**")

    # ---------- DOWNLOAD ----------
    @commands.command(name="downaudio")
    @commands.guild_only()
    async def down_audio(self, ctx, url: str):
        config = await audiodown_col.find_one({"guild_id": ctx.guild.id})
        if not config:
            return await ctx.reply("❌ Audio download system is not setup.")

        if not (self.is_owner(ctx) or self.is_admin(ctx)):
            if ctx.channel.id != config["channel_id"]:
                try:
                    await ctx.message.delete()
                except:
                    pass

                warn = await ctx.send(
                    f"⚠ {ctx.author.mention} **Use the setup channel for downloads.**"
                )
                await asyncio.sleep(5)
                await warn.delete()
                return

        now = time.time()
        if now - config["last_done"] < 30:
            return await ctx.reply("⏳ **Cooldown active. Try again in 30 seconds.**")

        status = await ctx.reply("🔍 **Checking audio info...**")

        try:
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            if info.get("_type") == "playlist" or "entries" in info:
                await status.edit(content="❌ **Playlist links are not allowed.**")
                return

            filesize = info.get("filesize") or info.get("filesize_approx")
            if not filesize:
                await status.edit(content="❌ **Unable to determine audio size.**")
                return

            if filesize / (1024 * 1024) > 7:
                await status.edit("❌ **Audio exceeds 7 MB limit.**")
                return

        except Exception:
            await status.edit("❌ **Failed to fetch audio info.**")
            return

        await status.edit("🎧 **Downloading audio...**")

        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": "audio_%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            await ctx.send(
                content=f"🎵 **Requested by {ctx.author.mention}**",
                file=discord.File(file_path)
            )

            await audiodown_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$set": {"last_done": time.time()}}
            )

            await status.delete()
            os.remove(file_path)

        except Exception as e:
            await status.edit("❌ **Audio download failed.**")
            print(f"[DOWN AUDIO ERROR] {e}")

async def setup(bot):
    await bot.add_cog(Mp3Downloader(bot))
