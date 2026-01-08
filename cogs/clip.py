import discord
from discord.ext import commands
import pytchat
import asyncio
import re
import time
from datetime import datetime, timezone
from collections import deque


MAX_CLIPS_PER_MINUTE = 1


class Clip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # guild_id -> session data

    # ---------------- PERMISSION ----------------
    def can_manage(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    # ---------------- TIME HELPERS ----------------
    def hms_to_seconds(self, t):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s

    def seconds_to_hms(self, sec):
        return f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}"

    # ================= CLIP ON =================
    @commands.command(name="clipon")
    @commands.guild_only()
    async def clipon(self, ctx, channel: discord.TextChannel, stream_url: str):
        if not self.can_manage(ctx):
            return await ctx.reply("❌ Admin / Owner only.")

        if ctx.guild.id in self.sessions:
            return await ctx.reply("⚠️ Clip system already running in this server.")

        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.reply("❌ I cannot send messages in that channel.")

        match = re.search(r"(?:v=|\/live\/)([a-zA-Z0-9_-]+)", stream_url)
        if not match:
            return await ctx.reply("❌ Invalid YouTube Live URL.")

        video_id = match.group(1)
        chat = pytchat.create(video_id=video_id)

        session = {
            "video_id": video_id,
            "chat": chat,
            "task": None,
            "clip_channel_id": channel.id,
            "script_start": time.time(),
            "sync_base": None,
            "sync_time": None,
            "rate": deque()
        }

        task = asyncio.create_task(self.listen_chat(ctx.guild.id))
        session["task"] = task

        self.sessions[ctx.guild.id] = session

        await ctx.reply(
            f"✅ **Clip System Enabled**\n"
            f"🎥 Stream ID: `{video_id}`\n"
            f"📍 Channel: {channel.mention}\n\n"
            f"Use `!sync HH:MM:SS` if needed."
        )

    # ================= CLIP OFF =================
    @commands.command(name="clipoff")
    @commands.guild_only()
    async def clipoff(self, ctx):
        if not self.can_manage(ctx):
            return await ctx.reply("❌ Admin / Owner only.")

        session = self.sessions.pop(ctx.guild.id, None)
        if not session:
            return await ctx.reply("⚠️ Clip system is not running.")

        session["task"].cancel()
        session["chat"].terminate()

        await ctx.reply("🛑 Clip system disabled.")

    # ================= SYNC =================
    @commands.command(name="sync")
    @commands.guild_only()
    async def sync(self, ctx, time_str: str):
        if not self.can_manage(ctx):
            return await ctx.reply("❌ Admin / Owner only.")

        session = self.sessions.get(ctx.guild.id)
        if not session:
            return await ctx.reply("⚠️ Clip system not running.")

        try:
            session["sync_base"] = self.hms_to_seconds(time_str)
            session["sync_time"] = time.time()
            await ctx.reply(f"✅ Synced at `{time_str}`")
        except Exception:
            await ctx.reply("❌ Invalid format. Use HH:MM:SS")

    # ================= STATUS =================
    @commands.command(name="statusclip")
    @commands.guild_only()
    async def statusclip(self, ctx):
        session = self.sessions.get(ctx.guild.id)
        if not session:
            return await ctx.reply("🔴 Clip system OFF")

        await ctx.reply(
            f"🟢 Clip system ON\n"
            f"🎥 Stream ID: `{session['video_id']}`"
        )

    # ================= CHAT LISTENER =================
    async def listen_chat(self, guild_id: int):
        session = self.sessions[guild_id]
        chat = session["chat"]

        try:
            while chat.is_alive():
                for c in chat.get().sync_items():
                    text = c.message.strip().lower()

                    if not text.startswith("!clip"):
                        continue

                    if not (c.author.isChatOwner or c.author.isChatModerator):
                        continue

                    # RATE LIMIT
                    now = time.time()
                    rate = session["rate"]
                    while rate and now - rate[0] > 60:
                        rate.popleft()

                    if len(rate) >= MAX_CLIPS_PER_MINUTE:
                        continue

                    rate.append(now)

                    name = c.message[6:].strip() or "No name"

                    if session["sync_base"] is not None:
                        sec = int(
                            session["sync_base"]
                            + (now - session["sync_time"])
                        )
                    else:
                        sec = int(now - session["script_start"])

                    ts = self.seconds_to_hms(sec)
                    url = (
                        f"https://www.youtube.com/watch?v="
                        f"{session['video_id']}&t={sec}s"
                    )

                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue

                    channel = guild.get_channel(session["clip_channel_id"])
                    if not channel:
                        continue

                    role = "Owner" if c.author.isChatOwner else "Moderator"

                    embed = discord.Embed(
                        title="🎬 Clip Requested",
                        description=(
                            f"**By:** {c.author.name} ({role})\n"
                            f"**Name:** {name}\n"
                            f"**Timestamp:** `{ts}`"
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc)
                    )

                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Open Clip",
                            url=url,
                            style=discord.ButtonStyle.link
                        )
                    )

                    await channel.send(embed=embed, view=view)

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

    # ================= CLEANUP =================
    def cog_unload(self):
        for s in self.sessions.values():
            s["task"].cancel()
            s["chat"].terminate()


async def setup(bot):
    await bot.add_cog(Clip(bot))
