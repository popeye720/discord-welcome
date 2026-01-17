import os
import asyncio
import traceback
import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import aiohttp

# ✅ BRAND SYSTEM (SAME)
BRAND_URL = "https://discord.gg/DVqvtsYNy7"
BRAND_TITLE = "MUSIC PROVIED BY TEJAS"


def format_duration_ms(ms: int | None) -> str:
    if not ms or ms <= 0:
        return "Unknown"
    total_s = ms // 1000
    m = total_s // 60
    s = total_s % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


class Track:
    def __init__(self, playable: wavelink.Playable, requester_id: int):
        self.playable = playable
        self.requester_id = requester_id

    @property
    def title(self) -> str:
        return getattr(self.playable, "title", "Unknown")

    @property
    def author(self) -> str:
        return getattr(self.playable, "author", None) or getattr(self.playable, "artist", None) or "Unknown"

    @property
    def duration_ms(self) -> int | None:
        return getattr(self.playable, "length", None) or getattr(self.playable, "duration", None)

    @property
    def uri(self) -> str:
        return getattr(self.playable, "uri", "") or getattr(self.playable, "url", "") or ""


class GuildMusicState:
    def __init__(self):
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.current: Track | None = None
        self.loop_enabled: bool = False

        self.bassboost_enabled: bool = False
        self.bass_gain_db: int = 8
        self.eightd_enabled: bool = False

        self.panel_channel_id: int | None = None
        self.panel_message_id: int | None = None

        self.player_task: asyncio.Task | None = None
        self.stopped: bool = False


class MusicPanelView(discord.ui.View):
    def __init__(self, cog: "Music", guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        player = self.cog.get_player(guild)
        if not player or not getattr(player, "connected", False) or not getattr(player, "channel", None):
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return False

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await interaction.response.send_message("You must be in the same voice channel as the bot.", ephemeral=True)
            return False

        if member.voice.channel.id != player.channel.id:
            await interaction.response.send_message("You must be in the same voice channel as the bot.", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="▶️ Play", style=discord.ButtonStyle.secondary, custom_id="music_play")
    async def btn_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_play(interaction)

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="music_pause")
    async def btn_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_pause(interaction)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_skip(interaction)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="music_loop")
    async def btn_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_loop(interaction)

    @discord.ui.button(label="📶 Bass", style=discord.ButtonStyle.secondary, custom_id="music_bassboost")
    async def btn_bassboost(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_bassboost(interaction)

    @discord.ui.button(label="♾️ 8D", style=discord.ButtonStyle.secondary, custom_id="music_8d")
    async def btn_8d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_8d(interaction)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.secondary, custom_id="music_stop")
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_stop(interaction)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}
        self._voice_locks: dict[int, asyncio.Lock] = {}
        self._node_ready = asyncio.Event()

    # ---------- helpers ----------
    def _get_voice_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self._voice_locks:
            self._voice_locks[guild_id] = asyncio.Lock()
        return self._voice_locks[guild_id]

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    def _brand_color(self, guild: discord.Guild) -> discord.Color:
        return discord.Color.from_rgb(2, 102, 255)

    def get_player(self, guild: discord.Guild) -> wavelink.Player | None:
        vc = guild.voice_client
        return vc if isinstance(vc, wavelink.Player) else None

    async def _safe_ephemeral(self, interaction: discord.Interaction, content: str):
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, ephemeral=True)
        except:
            pass


    async def _preflight(self, base_url: str, password: str) -> int:
        url = base_url.rstrip("/") + "/v4/info"
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"Authorization": password}) as r:
                    text = await r.text()
                    print(f"✅ Lavalink preflight {r.status} {url}")
                    if r.status != 200:
                        print("❌ Preflight body:", text[:400])
                    return r.status
        except Exception as e:
            print("❌ Preflight failed:", type(e).__name__, repr(e))
            return 0

    async def connect_node_from_env(self):
        if self._node_ready.is_set():
            return

        raw = os.getenv("LAVALINK_URI", "").strip()
        password = os.getenv("LAVALINK_PASSWORD", "").strip()

        if not raw or not password:
            raise RuntimeError("Missing ENV: LAVALINK_URI or LAVALINK_PASSWORD")

        # HTTP url for preflight
        if raw.startswith("wss://"):
            http_url = "https://" + raw[len("wss://"):]
        elif raw.startswith("ws://"):
            http_url = "http://" + raw[len("ws://"):]
        elif raw.startswith(("https://", "http://")):
            http_url = raw
        else:
            http_url = "https://" + raw

        # WS url for node
        if raw.startswith("https://"):
            ws_url = "wss://" + raw[len("https://"):]
        elif raw.startswith("http://"):
            ws_url = "ws://" + raw[len("http://"):]
        elif raw.startswith(("wss://", "ws://")):
            ws_url = raw
        else:
            ws_url = "wss://" + raw

        print("🔌 Connecting Lavalink (HTTP preflight):", http_url)
        status = await self._preflight(http_url, password)

        if status != 200:
            print("❌ Skipping WS connect because preflight is not OK.")
            return

        print("🔌 Connecting Lavalink (WS node):", ws_url)

        try:
            node = wavelink.Node(
                uri=ws_url,
                password=password,
                identifier="main"   # ✅ helps debugging / stability
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            print("✅ Lavalink node connected:", ws_url)
            self._node_ready.set()
        except Exception as e:
            print("❌ Lavalink connect failed:", type(e).__name__, repr(e))
            traceback.print_exc()
            raise




    async def ensure_voice(self, interaction: discord.Interaction) -> wavelink.Player | None:
        guild = interaction.guild
        if not guild:
            return None

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await self._safe_ephemeral(interaction, "You must be in a voice channel.")
            return None

        await self._node_ready.wait()

        lock = self._get_voice_lock(guild.id)
        async with lock:
            player = self.get_player(guild)
            if player and getattr(player, "connected", False):
                if player.channel and member.voice.channel.id != player.channel.id:
                    await self._safe_ephemeral(interaction, "Bot is already connected in a different voice channel.")
                    return None
                return player

            try:
                player = await member.voice.channel.connect(cls=wavelink.Player)
                try:
                    await guild.change_voice_state(
                        channel=member.voice.channel,
                        self_mute=False,
                        self_deaf=True
                    )
                except:
                    pass
                return player
            except Exception as e:
                await self._safe_ephemeral(interaction, f"Voice connect failed: {e}")
                return None

    async def _ensure_same_vc(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False) or not getattr(player, "channel", None):
            await self._safe_ephemeral(interaction, "Bot is not connected to a voice channel.")
            return False

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await self._safe_ephemeral(interaction, "You must be in the same voice channel as the bot.")
            return False

        if member.voice.channel.id != player.channel.id:
            await self._safe_ephemeral(interaction, "You must be in the same voice channel as the bot.")
            return False

        return True

    async def apply_filters(self, guild: discord.Guild):
        st = self.get_state(guild.id)
        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return

        filters = wavelink.Filters()

        if st.bassboost_enabled:
            gain = max(0.0, min(0.8, (st.bass_gain_db / 25.0) * 0.8))
            filters.equalizer.set(band=0, gain=gain)
            filters.equalizer.set(band=1, gain=gain)
            filters.equalizer.set(band=2, gain=gain * 0.7)

        if st.eightd_enabled:
            filters.rotation.set(rotation_hz=0.08)

        await player.set_filters(filters)

    # ---------- embeds/panel ----------
    def build_now_playing_embed(self, guild: discord.Guild) -> discord.Embed:
        st = self.get_state(guild.id)
        t = st.current
        embed = discord.Embed(title=BRAND_TITLE, color=self._brand_color(guild))

        if not t:
            embed.description = "No track is playing."
            return embed

        embed.add_field(name=" ", value=f"[{t.title}]({BRAND_URL})", inline=False)
        embed.add_field(name="Requested By", value=f"<@{t.requester_id}>", inline=True)
        embed.add_field(name="Duration", value=format_duration_ms(t.duration_ms), inline=True)
        embed.add_field(name="Author", value=t.author or "Unknown", inline=True)
        embed.add_field(name="Loop", value="On" if st.loop_enabled else "Off", inline=True)
        embed.add_field(
            name="BassBoost 📶",
            value=("On" if st.bassboost_enabled else "Off") + (f" (Gain {st.bass_gain_db}db)" if st.bassboost_enabled else ""),
            inline=True
        )
        embed.add_field(name="8D ♾️", value="On" if st.eightd_enabled else "Off", inline=True)

        q_items = list(st.queue._queue)
        if q_items:
            preview = "\n".join([f"{i+1}. {x.title} ({format_duration_ms(x.duration_ms)})" for i, x in enumerate(q_items[:5])])
            embed.add_field(name="Queue", value=preview, inline=False)

        return embed

    async def get_panel_message(self, guild: discord.Guild) -> discord.Message | None:
        st = self.get_state(guild.id)
        if not st.panel_channel_id or not st.panel_message_id:
            return None
        ch = guild.get_channel(st.panel_channel_id)
        if not isinstance(ch, discord.TextChannel):
            return None
        try:
            return await ch.fetch_message(st.panel_message_id)
        except:
            return None

    async def upsert_panel_now_playing(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        embed = self.build_now_playing_embed(guild)
        view = MusicPanelView(self, guild.id)

        existing = await self.get_panel_message(guild)
        if existing:
            await existing.edit(embed=embed, view=view)
            return

        msg = await interaction.channel.send(embed=embed, view=view)
        st = self.get_state(guild.id)
        st.panel_channel_id = msg.channel.id
        st.panel_message_id = msg.id

    async def _refresh_panel_by_guild(self, guild: discord.Guild):
        msg = await self.get_panel_message(guild)
        if msg:
            try:
                await msg.edit(embed=self.build_now_playing_embed(guild), view=MusicPanelView(self, guild.id))
            except:
                pass

    async def finish_and_cleanup(self, guild: discord.Guild):
        st = self.get_state(guild.id)

        st.current = None
        st.loop_enabled = False
        st.bassboost_enabled = False
        st.bass_gain_db = 8
        st.eightd_enabled = False
        st.stopped = False

        while not st.queue.empty():
            try:
                st.queue.get_nowait()
            except:
                break

        player = self.get_player(guild)
        if player and getattr(player, "connected", False):
            try:
                await player.disconnect()
            except:
                pass

        st.panel_channel_id = None
        st.panel_message_id = None

    # ---------- playback loop ----------
    async def player_loop(self, guild_id: int):
        st = self.get_state(guild_id)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        while True:
            if st.stopped:
                await self.finish_and_cleanup(guild)
                return

            player = self.get_player(guild)
            if not player or not getattr(player, "connected", False):
                await self.finish_and_cleanup(guild)
                return

            try:
                track = await asyncio.wait_for(st.queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                if not st.current and st.queue.empty() and not getattr(player, "playing", False):
                    await self.finish_and_cleanup(guild)
                    return
                continue

            st.current = track

            try:
                await player.play(track.playable)
            except Exception as e:
                print("❌ player.play failed:", e)
                traceback.print_exc()
                st.current = None
                continue

            # apply filters AFTER starting playback
            await asyncio.sleep(0.25)
            await self.apply_filters(guild)

            while getattr(player, "playing", False) or getattr(player, "paused", False):
                if st.stopped:
                    try:
                        await player.stop()
                    except:
                        pass
                    break
                await asyncio.sleep(1.0)

            if st.loop_enabled and not st.stopped and st.current:
                await st.queue.put(st.current)

            st.current = None

            if st.queue.empty() and not st.loop_enabled and not st.stopped:
                await self.finish_and_cleanup(guild)
                return

    # ---------- buttons ----------
    async def _btn_play(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "paused", False):
            await player.resume()
            await interaction.followup.send("Resumed.", ephemeral=True)
        else:
            await interaction.followup.send("Already playing.", ephemeral=True)

        await self._refresh_panel_by_guild(guild)

    async def _btn_pause(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "playing", False) and not getattr(player, "paused", False):
            await player.pause(True)
            await interaction.followup.send("Paused.", ephemeral=True)
        else:
            await interaction.followup.send("Nothing is playing.", ephemeral=True)

        await self._refresh_panel_by_guild(guild)

    async def _btn_skip(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "playing", False) or getattr(player, "paused", False):
            await player.stop()
            await interaction.followup.send("Skipped.", ephemeral=True)
        else:
            await interaction.followup.send("Nothing to skip.", ephemeral=True)

        await self._refresh_panel_by_guild(guild)

    async def _btn_loop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        st = self.get_state(guild.id)
        st.loop_enabled = not st.loop_enabled
        await interaction.followup.send(f"Loop: {'On' if st.loop_enabled else 'Off'}", ephemeral=True)
        await self._refresh_panel_by_guild(guild)

    async def _btn_bassboost(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        st = self.get_state(guild.id)
        st.bassboost_enabled = not st.bassboost_enabled
        await self.apply_filters(guild)
        await interaction.followup.send(
            f"BassBoost 📶: {'On' if st.bassboost_enabled else 'Off'}"
            + (f" | Gain: {st.bass_gain_db}db" if st.bassboost_enabled else ""),
            ephemeral=True
        )
        await self._refresh_panel_by_guild(guild)

    async def _btn_8d(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        st = self.get_state(guild.id)
        st.eightd_enabled = not st.eightd_enabled
        await self.apply_filters(guild)
        await interaction.followup.send(f"8D ♾️: {'On' if st.eightd_enabled else 'Off'}", ephemeral=True)
        await self._refresh_panel_by_guild(guild)

    async def _btn_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return
        st = self.get_state(guild.id)
        st.stopped = True

        player = self.get_player(guild)
        if player and getattr(player, "connected", False):
            try:
                await player.stop()
            except:
                pass

        await interaction.followup.send("Stopped.", ephemeral=True)

    # ---------- slash commands ----------
    @app_commands.command(name="play", description="Play a song by name or URL")
    @app_commands.describe(query="Song name or URL")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            return await interaction.edit_original_response(content="Guild only.")

        player = await self.ensure_voice(interaction)
        if not player:
            return await interaction.edit_original_response(content="Voice connect failed.")

        st = self.get_state(guild.id)

        try:
            # ✅ Search (Railway compatible) - force YouTube (not YouTube Music)
            if query.startswith("http://") or query.startswith("https://"):
                results = await wavelink.Playable.search(query)
            else:
                results = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)

            # Normalize results
            playables: list[wavelink.Playable] = []
            if results is None:
                playables = []
            elif isinstance(results, wavelink.Playlist):
                playables = list(results)
            elif isinstance(results, (list, tuple)):
                playables = list(results[:1])
            else:
                playables = [results]

            if not playables:
                return await interaction.edit_original_response(content="No tracks found.")

            is_idle = (
                st.current is None
                and st.queue.empty()
                and not (getattr(player, "playing", False) or getattr(player, "paused", False))
            )

            if st.stopped:
                st.stopped = False

            for p in playables:
                await st.queue.put(Track(playable=p, requester_id=interaction.user.id))

            if is_idle:
                if not st.player_task or st.player_task.done():
                    st.player_task = self.bot.loop.create_task(self.player_loop(guild.id))

                await asyncio.sleep(0.2)
                await self.upsert_panel_now_playing(interaction)
                await interaction.edit_original_response(content="Started.")
            else:
                await interaction.edit_original_response(content=f"Queued: {len(playables)} track(s).")

        except Exception as e:
            print("❌ /play failed:", e)
            traceback.print_exc()
            await interaction.edit_original_response(content=f"Play failed: {e}")

    @app_commands.command(name="pause", description="Pause current song (same VC only)")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        if not await self._ensure_same_vc(interaction):
            return
        await self._btn_pause(interaction)

    @app_commands.command(name="skip", description="Skip current song (same VC only)")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        if not await self._ensure_same_vc(interaction):
            return
        await self._btn_skip(interaction)

    @app_commands.command(name="loop", description="Toggle loop on/off (same VC only)")
    @app_commands.guild_only()
    async def loop(self, interaction: discord.Interaction):
        if not await self._ensure_same_vc(interaction):
            return
        await self._btn_loop(interaction)

    @app_commands.command(name="stop", description="Stop playback and clear (same VC only)")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        if not await self._ensure_same_vc(interaction):
            return
        await self._btn_stop(interaction)

    @app_commands.command(name="resume", description="Resume if paused (same VC only)")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        if not await self._ensure_same_vc(interaction):
            return
        await self._btn_play(interaction)


async def setup(bot: commands.Bot):
    cog = Music(bot)
    await bot.add_cog(cog)

    # ✅ This runs during bot startup when extension loads (Railway safe)
    try:
        await cog.connect_node_from_env()
    except Exception as e:
        print("❌ Lavalink node connect failed on setup:", e)
