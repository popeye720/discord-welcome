import discord
from discord.ext import commands
from discord import app_commands

import pytchat
import asyncio
import re
import time
from datetime import datetime, timezone
from collections import deque

# ✅ CENTRALIZED UTILS
from utils.permissions import is_admin_or_guild_owner
from utils.interaction import safe_ephemeral


MAX_CLIPS_PER_MINUTE = 1
CLIP_OFFSET_SECONDS = 40  # ✅ NEW: make clip link 40 seconds earlier


class Clip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: dict[int, dict] = {}  # guild_id -> session data

    # ----------------- PERMISSION (ADMIN / OWNER) -----------------
    def can_manage(self, interaction: discord.Interaction) -> bool:
        return is_admin_or_guild_owner(interaction)

    async def deny_silent(self, interaction: discord.Interaction) -> bool:
        """
        streammode-style: if no perms, reply EPHEMERAL only to that user (no public leak)
        Returns True if denied (and replied), else False.
        """
        if self.can_manage(interaction):
            return False

        await safe_ephemeral(interaction, "❌ Admin / Owner only.")
        return True

    # ----------------- TIME HELPERS -----------------
    def hms_to_seconds(self, t: str) -> int:
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s

    def seconds_to_hms(self, sec: int) -> str:
        return f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}"

    def extract_video_id(self, stream_url: str) -> str | None:
        # Supports: ?v=VIDEO_ID , /live/VIDEO_ID , youtu.be/VIDEO_ID
        patterns = [
            r"(?:v=)([a-zA-Z0-9_-]{6,})",
            r"(?:\/live\/)([a-zA-Z0-9_-]{6,})",
            r"(?:youtu\.be\/)([a-zA-Z0-9_-]{6,})",
        ]
        for p in patterns:
            m = re.search(p, stream_url)
            if m:
                return m.group(1)
        return None

    # ========================= /clip GROUP =========================
    clip = app_commands.Group(name="clip", description="YouTube live clip system (Admin/Owner only)")

    # ========================= /clip on =========================
    @clip.command(name="on", description="Enable clip system for a YouTube live stream")
    @app_commands.guild_only()
    @app_commands.describe(
        channel="Discord channel where clip embeds will be sent",
        stream_url="YouTube Live URL (or video URL)"
    )
    async def clip_on(self, interaction: discord.Interaction, channel: discord.TextChannel, stream_url: str):
        if await self.deny_silent(interaction):
            return

        guild = interaction.guild
        assert guild is not None

        if guild.id in self.sessions:
            await safe_ephemeral(interaction, "⚠️ Clip system already running in this server.")
            return

        # Bot permission check in target channel
        me = guild.me or guild.get_member(self.bot.user.id)
        if not me:
            await safe_ephemeral(interaction, "❌ Bot member not found in guild.")
            return

        perms = channel.permissions_for(me)
        if not perms.send_messages:
            await safe_ephemeral(interaction, "❌ I cannot send messages in that channel.")
            return

        video_id = self.extract_video_id(stream_url)
        if not video_id:
            await safe_ephemeral(interaction, "❌ Invalid YouTube Live URL.")
            return

        await safe_ephemeral(interaction, "🔄 Enabling clip system...")

        try:
            chat = pytchat.create(video_id=video_id)
        except Exception as e:
            await safe_ephemeral(interaction, f"❌ Failed to start pytchat: `{type(e).__name__}`")
            return

        session = {
            "video_id": video_id,
            "chat": chat,
            "task": None,
            "clip_channel_id": channel.id,
            "script_start": time.time(),
            "sync_base": None,
            "sync_time": None,
            "rate": deque(),
        }

        task = asyncio.create_task(self.listen_chat(guild.id))
        session["task"] = task
        self.sessions[guild.id] = session

        await safe_ephemeral(
            interaction,
            f"✅ **Clip System Enabled**\n"
            f"🎥 Stream ID: `{video_id}`\n"
            f"📍 Channel: {channel.mention}\n\n"
            f"Use `/clip sync HH:MM:SS` if needed."
        )

    # ========================= /clip off =========================
    @clip.command(name="off", description="Disable clip system in this server")
    @app_commands.guild_only()
    async def clip_off(self, interaction: discord.Interaction):
        if await self.deny_silent(interaction):
            return

        guild = interaction.guild
        assert guild is not None

        session = self.sessions.pop(guild.id, None)
        if not session:
            await safe_ephemeral(interaction, "⚠️ Clip system is not running.")
            return

        try:
            session["task"].cancel()
        except Exception:
            pass

        try:
            session["chat"].terminate()
        except Exception:
            pass

        await safe_ephemeral(interaction, "🛑 Clip system disabled.")

    # ========================= /clip sync =========================
    @clip.command(name="sync", description="Sync timestamp base (HH:MM:SS) for accurate clip time")
    @app_commands.guild_only()
    @app_commands.describe(time_str="Format: HH:MM:SS (example: 01:23:45)")
    async def clip_sync(self, interaction: discord.Interaction, time_str: str):
        if await self.deny_silent(interaction):
            return

        guild = interaction.guild
        assert guild is not None

        session = self.sessions.get(guild.id)
        if not session:
            await safe_ephemeral(interaction, "⚠️ Clip system not running.")
            return

        try:
            session["sync_base"] = self.hms_to_seconds(time_str)
            session["sync_time"] = time.time()
            await safe_ephemeral(interaction, f"✅ Synced at `{time_str}`")
        except Exception:
            await safe_ephemeral(interaction, "❌ Invalid format. Use `HH:MM:SS`")

    # ========================= /clip status =========================
    @clip.command(name="status", description="Check clip system status")
    @app_commands.guild_only()
    async def clip_status(self, interaction: discord.Interaction):
        guild = interaction.guild
        assert guild is not None

        session = self.sessions.get(guild.id)
        if not session:
            await safe_ephemeral(interaction, "🔴 Clip system **OFF**")
            return

        await safe_ephemeral(
            interaction,
            f"🟢 Clip system **ON**\n🎥 Stream ID: `{session['video_id']}`"
        )

    # ================= CHAT LISTENER =================
    async def listen_chat(self, guild_id: int):
        session = self.sessions.get(guild_id)
        if not session:
            return

        chat = session["chat"]

        try:
            while chat.is_alive():
                # session might be removed while running
                session = self.sessions.get(guild_id)
                if not session:
                    break

                for c in chat.get().sync_items():
                    msg_raw = (c.message or "").strip()
                    text = msg_raw.lower()

                    if not text.startswith("!clip"):
                        continue

                    # only yt owner/mod
                    try:
                        if not (c.author.isChatOwner or c.author.isChatModerator):
                            continue
                    except Exception:
                        continue

                    # RATE LIMIT
                    now = time.time()
                    rate: deque = session["rate"]
                    while rate and now - rate[0] > 60:
                        rate.popleft()

                    if len(rate) >= MAX_CLIPS_PER_MINUTE:
                        continue

                    rate.append(now)

                    name = msg_raw[5:].strip()  # after "!clip"
                    if name.startswith(":"):
                        name = name[1:].strip()
                    name = name or "No name"

                    if session["sync_base"] is not None and session["sync_time"] is not None:
                        sec = int(session["sync_base"] + (now - session["sync_time"]))
                    else:
                        sec = int(now - session["script_start"])

                    # ✅ NEW: go 40 seconds back, but never below 0
                    clip_sec = max(0, sec - CLIP_OFFSET_SECONDS)

                    ts = self.seconds_to_hms(clip_sec)
                    url = f"https://www.youtube.com/watch?v={session['video_id']}&t={clip_sec}s"

                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue

                    channel = guild.get_channel(session["clip_channel_id"])
                    if not channel:
                        continue

                    role = "Owner" if getattr(c.author, "isChatOwner", False) else "Moderator"

                    embed = discord.Embed(
                        title="🎬 Clip Requested",
                        description=(
                            f"**By:** {c.author.name} ({role})\n"
                            f"**Name:** {name}\n"
                            f"**Timestamp:** `{ts}`"
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc),
                    )

                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Open Clip",
                            url=url,
                            style=discord.ButtonStyle.link,
                        )
                    )

                    try:
                        await channel.send(embed=embed, view=view)
                    except Exception:
                        pass

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception:
            # keep it silent (no leak), but you can print for logs
            pass

    # ================= CLEANUP =================
    def cog_unload(self):
        for s in list(self.sessions.values()):
            try:
                s["task"].cancel()
            except Exception:
                pass
            try:
                s["chat"].terminate()
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Clip(bot))



