import discord
from discord.ext import commands
from discord import app_commands

import pytchat
import asyncio
import re
import time
from collections import deque
from typing import Deque, Dict, Tuple, Optional

# ✅ Centralized permission + safe reply
from utils.permissions import is_admin_or_guild_owner
from utils.interaction import safe_ephemeral


# ===================== TUNABLES (SAFE DEFAULTS) =====================

FLUSH_COOLDOWN_SECONDS = 2.0          # batch flush interval (per guild)
MAX_LINES_PER_FLUSH = 20              # max lines in one Discord message per guild

LISTEN_BASE_SLEEP = 1.0               # normal polling sleep
LISTEN_MAX_SLEEP = 5.0                # backoff max sleep on errors

SEEN_TTL_SECONDS = 10 * 60            # 10 min (same user re-allowed after TTL)
SEEN_MAX_SIZE = 5000                  # cap per guild (memory safe)

DISCORD_MAX_SENDS_PER_MINUTE = 20     # per guild safety cap
GLOBAL_SEND_CONCURRENCY = 5           # how many sends in parallel globally

MAX_ACTIVE_SESSIONS_PER_BOT = 150     # practical per-process limit


class ChatPoll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # guild_id -> session
        self.sessions: Dict[int, dict] = {}

        # One global flusher task (instead of 1 per guild)
        self._flush_task: Optional[asyncio.Task] = None

        # Global send semaphore (discord rate safety)
        self._send_sem = asyncio.Semaphore(GLOBAL_SEND_CONCURRENCY)

    # ----------------- PERMISSION (ADMIN / OWNER) -----------------
    def can_manage(self, interaction: discord.Interaction) -> bool:
        # ✅ Centralized
        return is_admin_or_guild_owner(interaction)

    async def deny_silent(self, interaction: discord.Interaction) -> bool:
        if self.can_manage(interaction):
            return False
        # ✅ Centralized safe ephemeral
        await safe_ephemeral(interaction, "❌ Admin / Owner only.")
        return True

    # ----------------- START GLOBAL FLUSHER SAFELY -----------------
    async def cog_load(self):
        # Start global flusher when cog is loaded
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._global_flush_loop())

    def cog_unload(self):
        # Stop everything
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()

        for guild_id, s in list(self.sessions.items()):
            try:
                s["stopping"] = True
            except Exception:
                pass
            try:
                t = s.get("task_listen")
                if t:
                    t.cancel()
            except Exception:
                pass
            try:
                s.get("chat") and s["chat"].terminate()
            except Exception:
                pass

        self.sessions.clear()

    # ----------------- YT URL -> VIDEO ID -----------------
    def extract_video_id(self, stream_url: str) -> str | None:
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

    def build_matcher(self, word: str):
        w = (word or "").strip()
        if not w:
            return lambda _t: False

        # alnum/_ => word boundary match, otherwise substring match
        if re.fullmatch(r"[A-Za-z0-9_]+", w):
            rgx = re.compile(rf"(?i)(?:^|\b){re.escape(w)}(?:\b|$)")
            return lambda t: bool(rgx.search(t or ""))
        else:
            wl = w.lower()
            return lambda t: wl in (t or "").lower()

    # ----------------- SEEN TTL HELPERS -----------------
    def _seen_prune(self, session: dict, now: float):
        # Remove expired entries from deque+set
        dq: Deque[Tuple[float, str]] = session["seen_deque"]
        st: set = session["seen_set"]

        cutoff = now - SEEN_TTL_SECONDS
        while dq and dq[0][0] < cutoff:
            ts, name = dq.popleft()
            # remove only if this exact name is not re-added later
            # (we keep it simple: if name exists in set, remove it)
            if name in st:
                st.discard(name)

        # Hard cap safety (prune oldest)
        while len(st) > SEEN_MAX_SIZE and dq:
            _, name = dq.popleft()
            st.discard(name)

    def _seen_check_and_add(self, session: dict, name: str, now: float) -> bool:
        """
        Returns True if allowed (not seen recently), and marks as seen.
        """
        self._seen_prune(session, now)
        st: set = session["seen_set"]
        dq: Deque[Tuple[float, str]] = session["seen_deque"]

        if name in st:
            return False

        st.add(name)
        dq.append((now, name))
        return True

    # ----------------- DISCORD SAFE SEND -----------------
    async def _safe_send(self, channel: discord.abc.Messageable, content: str):
        async with self._send_sem:
            try:
                await channel.send(content)
            except Exception:
                pass

    # ========================= /chatpoll GROUP =========================
    chatpoll = app_commands.Group(
        name="chatpoll",
        description="YouTube live chat poll (Admin/Owner only)"
    )

    # ========================= /chatpoll on =========================
    @chatpoll.command(
        name="on",
        description="Start polling YouTube live chat for a word and send matched user+message to a channel"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)  # UI hide from most non-admins
    @app_commands.describe(
        channel="Discord channel where matched user+message will be sent",
        stream_url="YouTube Live URL (or video URL)",
        word="Word/keyword to detect in live chat"
    )
    async def chatpoll_on(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        stream_url: str,
        word: str
    ):
        if await self.deny_silent(interaction):
            return

        guild = interaction.guild
        assert guild is not None

        if guild.id in self.sessions:
            return await interaction.response.send_message(
                "⚠️ ChatPoll already running in this server.",
                ephemeral=True
            )

        if len(self.sessions) >= MAX_ACTIVE_SESSIONS_PER_BOT:
            return await interaction.response.send_message(
                f"⚠️ Too many active sessions on this bot instance (limit: {MAX_ACTIVE_SESSIONS_PER_BOT}). "
                f"Please stop another poll first.",
                ephemeral=True
            )

        # Bot permission check in target channel
        me = guild.me or guild.get_member(self.bot.user.id)
        if not me:
            return await interaction.response.send_message("❌ Bot member not found in guild.", ephemeral=True)

        perms = channel.permissions_for(me)
        if not perms.send_messages:
            return await interaction.response.send_message("❌ I cannot send messages in that channel.", ephemeral=True)

        video_id = self.extract_video_id(stream_url)
        if not video_id:
            return await interaction.response.send_message("❌ Invalid YouTube URL.", ephemeral=True)

        word = (word or "").strip()
        if not word:
            return await interaction.response.send_message("❌ Word cannot be empty.", ephemeral=True)

        await interaction.response.send_message("🔄 Starting ChatPoll...", ephemeral=True)

        # Start pytchat
        try:
            chat = pytchat.create(video_id=video_id)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Failed to start pytchat: `{type(e).__name__}`",
                ephemeral=True
            )

        # Quick best-effort live-check
        try:
            ok = False
            start_check = time.time()
            while time.time() - start_check < 6:
                if chat.is_alive():
                    ok = True
                    break
                await asyncio.sleep(1)

            if not ok:
                try:
                    chat.terminate()
                except Exception:
                    pass
                return await interaction.followup.send(
                    "❌ Stream chat is not alive. Make sure the stream is **LIVE** and URL is correct.",
                    ephemeral=True
                )
        except Exception:
            try:
                chat.terminate()
            except Exception:
                pass
            return await interaction.followup.send(
                "❌ Could not verify live chat. Try again (stream must be LIVE).",
                ephemeral=True
            )

        now = time.time()
        session = {
            "video_id": video_id,
            "chat": chat,
            "task_listen": None,
            "target_channel_id": channel.id,

            "word": word,
            "matcher": self.build_matcher(word),

            "queue": deque(),  # (name, msg)
            "last_flush": 0.0,
            "next_flush_at": now + FLUSH_COOLDOWN_SECONDS,

            "seen_set": set(),
            "seen_deque": deque(),

            "discord_rate": deque(),  # timestamps of sends (per guild)

            "stopping": False,
            "listen_sleep": LISTEN_BASE_SLEEP,
        }

        session["task_listen"] = asyncio.create_task(self._listen_chat(guild.id))
        self.sessions[guild.id] = session

        await interaction.followup.send(
            f"✅ **ChatPoll Enabled**\n"
            f"🎥 Stream ID: `{video_id}`\n"
            f"📍 Channel: {channel.mention}\n"
            f"🔎 Word: `{word}`\n\n"
            f"Use `/chatpoll off` to stop.",
            ephemeral=True
        )

    # ========================= /chatpoll off =========================
    @chatpoll.command(name="off", description="Stop ChatPoll in this server")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def chatpoll_off(self, interaction: discord.Interaction):
        if await self.deny_silent(interaction):
            return

        guild = interaction.guild
        assert guild is not None

        session = self.sessions.pop(guild.id, None)
        if not session:
            return await interaction.response.send_message("⚠️ ChatPoll is not running.", ephemeral=True)

        await self._stop_session(guild.id, session, notify=False)
        await interaction.response.send_message("🛑 ChatPoll stopped.", ephemeral=True)

    # ========================= /chatpoll status =========================
    @chatpoll.command(name="status", description="Check ChatPoll status")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def chatpoll_status(self, interaction: discord.Interaction):
        guild = interaction.guild
        assert guild is not None

        session = self.sessions.get(guild.id)
        if not session:
            return await interaction.response.send_message("🔴 ChatPoll **OFF**", ephemeral=True)

        ch = guild.get_channel(session["target_channel_id"])
        ch_text = ch.mention if isinstance(ch, discord.TextChannel) else f"`{session['target_channel_id']}`"

        await interaction.response.send_message(
            f"🟢 ChatPoll **ON**\n"
            f"🎥 Stream ID: `{session['video_id']}`\n"
            f"🔎 Word: `{session['word']}`\n"
            f"📍 Channel: {ch_text}",
            ephemeral=True
        )

    # ================= LISTEN YT CHAT (PER GUILD) =================
    async def _listen_chat(self, guild_id: int):
        session = self.sessions.get(guild_id)
        if not session:
            return

        chat = session["chat"]
        matcher = session["matcher"]

        try:
            while chat.is_alive():
                # session might be removed while running
                session = self.sessions.get(guild_id)
                if not session or session.get("stopping"):
                    break

                got_any = False

                try:
                    items = chat.get().sync_items()
                    got_any = True
                except Exception:
                    items = []

                now = time.time()
                # prune seen occasionally
                self._seen_prune(session, now)

                for c in items:
                    msg = (getattr(c, "message", "") or "").strip()
                    if not msg:
                        continue

                    if not matcher(msg):
                        continue

                    author = getattr(c, "author", None)
                    try:
                        name = (getattr(author, "name", None) or "").strip()
                    except Exception:
                        name = ""
                    if not name:
                        continue

                    # TTL-based unique (avoid spam)
                    if not self._seen_check_and_add(session, name, now):
                        continue

                    session["queue"].append((name, msg))

                # Adaptive backoff: if errors/no data, increase sleep a bit
                if got_any:
                    session["listen_sleep"] = LISTEN_BASE_SLEEP
                else:
                    session["listen_sleep"] = min(LISTEN_MAX_SLEEP, session["listen_sleep"] + 0.5)

                await asyncio.sleep(session["listen_sleep"])

            # stream/chat stopped
            session = self.sessions.pop(guild_id, None)
            if session:
                await self._stop_session(guild_id, session, notify=True)

        except asyncio.CancelledError:
            pass
        except Exception:
            # silent
            session = self.sessions.pop(guild_id, None)
            if session:
                await self._stop_session(guild_id, session, notify=True)

    # ================= ONE GLOBAL FLUSH LOOP =================
    async def _global_flush_loop(self):
        try:
            while True:
                now = time.time()

                # iterate all sessions and flush those due
                for guild_id, session in list(self.sessions.items()):
                    if session.get("stopping"):
                        continue

                    # flush only if queue has data and time reached
                    if session["queue"] and now >= session.get("next_flush_at", 0):
                        await self._flush_once(guild_id, session, now)
                        session["next_flush_at"] = now + FLUSH_COOLDOWN_SECONDS

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        except Exception:
            # keep silent
            pass

    def _discord_rate_allow(self, session: dict, now: float) -> bool:
        rate: Deque[float] = session["discord_rate"]
        while rate and now - rate[0] > 60:
            rate.popleft()
        if len(rate) >= DISCORD_MAX_SENDS_PER_MINUTE:
            return False
        rate.append(now)
        return True

    async def _flush_once(self, guild_id: int, session: dict, now: float):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(session["target_channel_id"])
        if not channel:
            return

        # Per-guild discord send cap
        if not self._discord_rate_allow(session, now):
            # If rate capped, just postpone flush (queue remains)
            return

        lines = []
        # pop up to MAX_LINES_PER_FLUSH but also keep within 1900 chars
        total_chars = 0
        while session["queue"] and len(lines) < MAX_LINES_PER_FLUSH:
            name, msg = session["queue"].popleft()
            line = f"**{name}** — {msg}"
            # keep message safe length
            if total_chars + len(line) + 1 > 1900:
                # push back if nothing added yet, else stop here
                if not lines:
                    # hard truncate line
                    line = line[:1900]
                    lines.append(line)
                else:
                    # put back for next flush
                    session["queue"].appendleft((name, msg))
                break

            lines.append(line)
            total_chars += len(line) + 1

        if not lines:
            return

        await self._safe_send(channel, "\n".join(lines))

    # ================= STOP SESSION =================
    async def _stop_session(self, guild_id: int, session: dict, notify: bool):
        session["stopping"] = True

        try:
            t = session.get("task_listen")
            if t:
                t.cancel()
        except Exception:
            pass

        try:
            session.get("chat") and session["chat"].terminate()
        except Exception:
            pass

        if notify:
            try:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    ch = guild.get_channel(session["target_channel_id"])
                    if ch:
                        await self._safe_send(ch, "🛑 Stream ended / chat stopped. **ChatPoll auto-stopped.**")
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatPoll(bot))
