import os
import discord
from discord.ext import commands
import pytchat
import re
import time
import asyncio
from datetime import datetime, timezone

OWNER_ID = int(os.getenv("OWNER_ID"))


class Clip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_task = None
        self.chat = None
        self.video_id = None
        self.script_start_time = None
        self.base_stream_seconds = None
        self.sync_system_time = None
        self.clip_channel = None

    # =========================
    # HELPERS
    # =========================
    def hms_24_to_seconds(self, time_str):
        dt = datetime.strptime(time_str, "%H:%M:%S")
        return dt.hour * 3600 + dt.minute * 60 + dt.second

    def seconds_to_hms(self, seconds: int):
        return f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

    # =========================
    # CLIP ON
    # =========================
    @commands.command(name="clipon")
    async def clipon(self, ctx, clip_channel: discord.TextChannel, stream_url: str):

        if ctx.author.id != OWNER_ID:
            return await ctx.reply("❌ You are not allowed to use this command")

        if self.chat_task:
            return await ctx.reply("⚠️ Clip system already running")

        if not clip_channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.reply("❌ I can't send messages in that channel")

        match = re.search(r"(?:v=|\/live\/)([a-zA-Z0-9_-]+)", stream_url)
        if not match:
            return await ctx.reply("❌ Invalid YouTube Live URL")

        self.video_id = match.group(1)
        self.clip_channel = clip_channel
        self.script_start_time = time.time()
        self.base_stream_seconds = None
        self.sync_system_time = None

        self.chat = pytchat.create(video_id=self.video_id)
        self.chat_task = asyncio.create_task(self.listen_chat())

        await ctx.reply(
            f"✅ **Clip system ON**\n"
            f"📺 Stream ID: `{self.video_id}`\n"
            f"📌 Clip Channel: {clip_channel.mention}\n\n"
            f"Use `!sync HH:MM:SS` in **Discord** (24-hour, optional)"
        )

    # =========================
    # CLIP OFF
    # =========================
    @commands.command(name="clipoff")
    async def clipoff(self, ctx):
        if ctx.author.id != OWNER_ID:
            return await ctx.reply("❌ You are not allowed")

        if self.chat_task:
            self.chat_task.cancel()
            self.chat_task = None
            self.chat = None
            await ctx.reply("🛑 **Clip system OFF**")
        else:
            await ctx.reply("⚠️ Clip system not running")

    # =========================
    # SYNC
    # =========================
    @commands.command(name="sync")
    async def sync(self, ctx, *, time_str: str):
        if ctx.author.id != OWNER_ID:
            return await ctx.reply("❌ You are not allowed")

        if not self.chat_task:
            return await ctx.reply("⚠️ Clip system is not active. Use `!clipon` first.")

        try:
            self.base_stream_seconds = self.hms_24_to_seconds(time_str)
            self.sync_system_time = time.time()
            await ctx.reply(f"🔄 **SYNCED** at `{time_str}`")
        except:
            await ctx.reply("❌ Use format: `!sync HH:MM:SS` (24-hour)")

    # =========================
    # YOUTUBE CHAT LISTENER
    # =========================
    async def listen_chat(self):
        try:
            while self.chat and self.chat.is_alive():
                for c in self.chat.get().sync_items():
                    text = c.message.strip()

                    if not text.lower().startswith("!clip"):
                        continue

                    parts = text.split(" ", 1)
                    clip_name = parts[1] if len(parts) > 1 else "No name"

                    now = time.time()

                    if self.base_stream_seconds is not None:
                        seconds = int(self.base_stream_seconds + (now - self.sync_system_time))
                    else:
                        seconds = int(now - self.script_start_time)

                    timestamp = self.seconds_to_hms(seconds)
                    clip_url = f"https://www.youtube.com/watch?v={self.video_id}&t={seconds}s"

                    if c.author.isChatOwner:
                        role = "Owner"
                    elif c.author.isChatModerator:
                        role = "Moderator"
                    else:
                        role = "Viewer"

                    embed = discord.Embed(
                        title="🎬 Clip Requested",
                        description=(
                            f"👤 **User** : {c.author.name} ({role})\n"
                            f"🏷️ **Clip Name** : {clip_name}\n"
                            f"⏱️ **Timestamp** : `{timestamp}`"
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc)
                    )

                    embed.set_footer(text="YouTube Live Clip System")

                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Open clip",
                            url=clip_url,
                            style=discord.ButtonStyle.link
                        )
                    )

                    await self.clip_channel.send(embed=embed, view=view)

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

    # =========================
    # CLEANUP
    # =========================
    def cog_unload(self):
        if self.chat_task:
            self.chat_task.cancel()


async def setup(bot):
    await bot.add_cog(Clip(bot))
