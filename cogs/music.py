import asyncio
import time
import traceback
import os
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
import wavelink

# ✅ BRAND SYSTEM (SAME)
BRAND_URL = "https://discord.gg/DVqvtsYNy7"
BRAND_TITLE = "MUSIC PROVIDED BY TEJAS"


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

def build_idle_leave_embed(self, guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=BRAND_TITLE,
        url=BRAND_URL,
        color=self._brand_color(guild)
    )
    embed.description = (
        "I have left the voice channel due to inactivity. "
        "Use /play to summon me again!"
    )
    return embed

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
        self.current: Optional[Track] = None

        # ✅ only 8D filter remains
        self.eightd_enabled: bool = False

        # ✅ loop current song
        self.loop_enabled: bool = False

        # panel storage (for current playing panel only)
        self.panel_channel_id: Optional[int] = None
        self.panel_message_id: Optional[int] = None

        self.player_task: Optional[asyncio.Task] = None
        self.stopped: bool = False

        # ✅ 1-second global (per-guild) button cooldown
        self.cooldown_until: float = 0.0

        # last play channel (where we should post "queue ended" as NEW embed)
        self.last_play_text_channel_id: Optional[int] = None


class MusicPanelView(discord.ui.View):
    def __init__(self, cog: "Music", guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        st = self.cog.get_state(guild.id)

        # ✅ 1 second safety cooldown for everyone
        now = time.monotonic()
        if now < st.cooldown_until:
            try:
                await interaction.response.send_message("⏳ Wait 1 second...", ephemeral=True)
            except:
                pass
            return False

        player = self.cog.get_player(guild)
        if not player or not getattr(player, "connected", False) or not getattr(player, "channel", None):
            await self.cog._safe_ephemeral(interaction, "Bot is not connected to a voice channel.")
            return False

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await self.cog._safe_ephemeral(interaction, "You must be in the same voice channel as the bot.")
            return False

        if member.voice.channel.id != player.channel.id:
            await self.cog._safe_ephemeral(interaction, "You must be in the same voice channel as the bot.")
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

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.secondary, custom_id="music_stop")
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_stop(interaction)

    @discord.ui.button(label="♾️ 8D", style=discord.ButtonStyle.secondary, custom_id="music_8d")
    async def btn_8d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_8d(interaction)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="music_loop")
    async def btn_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._btn_loop(interaction)


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

    def get_player(self, guild: discord.Guild) -> Optional[wavelink.Player]:
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

    async def _connect_node(self):
        if self._node_ready.is_set():
            return

        # ✅ Railway / env based
        uri = (os.getenv("LAVALINK_URI") or "").strip().rstrip("/")
        password = (os.getenv("LAVALINK_PASSWORD") or "").strip()

        # ✅ If missing -> DON'T crash, just keep music disabled
        if not uri or not password:
            print("⚠️ Music disabled: set LAVALINK_URI and LAVALINK_PASSWORD env vars to enable Lavalink.")
            return

        try:
            node = wavelink.Node(uri=uri, password=password)
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            print("✅ Lavalink node connected:", uri)
            self._node_ready.set()
        except Exception as e:
            # ✅ If wrong URI/password or Lavalink down -> DON'T crash, keep disabled
            print("❌ Lavalink node connect failed (music disabled):", e)

    async def ensure_voice(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        guild = interaction.guild
        if not guild:
            return None

        # ✅ If Lavalink not ready, tell user nicely (no crash)
        if not self._node_ready.is_set():
            await self._safe_ephemeral(interaction, "⚠️ Music is currently disabled (Lavalink not configured).")
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
                    await guild.change_voice_state(channel=member.voice.channel, self_mute=False, self_deaf=True)
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

    # ---------- filters (ONLY 8D) ----------
    async def apply_filters(self, guild: discord.Guild):
        st = self.get_state(guild.id)
        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return

        filters = wavelink.Filters()
        if st.eightd_enabled:
            try:
                # Fixed for Wavelink 3.x
                filters.rotation = wavelink.Rotation(rotation_hz=0.08)
            except:
                pass

        try:
            await player.set_filters(filters)
        except Exception as e:
            print("❌ set_filters failed:", e)

    # ---------- embeds ----------
    def _base_embed(self, guild: discord.Guild) -> discord.Embed:
        return discord.Embed(
            title=BRAND_TITLE,
            color=self._brand_color(guild)
        )

    def build_now_playing_embed(self, guild: discord.Guild) -> discord.Embed:
        st = self.get_state(guild.id)
        embed = self._base_embed(guild)

        t = st.current
        if not t:
            embed.description = "No track is playing."
            return embed
        
        embed.description = f"**[{t.title}]({BRAND_URL})**"
        
        embed.add_field(name="Requested By", value=f"<@{t.requester_id}>", inline=True)
        embed.add_field(name="Duration", value=format_duration_ms(t.duration_ms), inline=True)
        embed.add_field(name="Author", value=t.author or "Unknown", inline=True)

        embed.add_field(name="8D", value="On" if st.eightd_enabled else "Off", inline=True)
        embed.add_field(name="Loop", value="On" if getattr(st, "loop_enabled", False) else "Off", inline=True)
        embed.add_field(name="Queue", value=f"{st.queue.qsize()} track(s)" if not st.queue.empty() else "(empty)", inline=True)

        return embed

    def build_queue_ended_embed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(
            title=BRAND_TITLE,
            url=BRAND_URL,
            color=self._brand_color(guild)
        )
        embed.description = (
            "All songs have been played! "
            "You can add songs again using /play command."
        )
        return embed

    async def get_panel_message(self, guild: discord.Guild) -> Optional[discord.Message]:
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

    async def set_panel(self, channel: discord.TextChannel, guild: discord.Guild, *, embed: discord.Embed, view: Optional[discord.ui.View]):
        st = self.get_state(guild.id)

        existing = await self.get_panel_message(guild)
        if existing:
            try:
                await existing.edit(embed=embed, view=view)
                return
            except:
                pass

        msg = await channel.send(embed=embed, view=view)
        st.panel_channel_id = msg.channel.id
        st.panel_message_id = msg.id

    async def refresh_panel(self, guild: discord.Guild, *, keep_buttons: bool = True):
        msg = await self.get_panel_message(guild)
        if not msg:
            return
        try:
            view = MusicPanelView(self, guild.id) if keep_buttons else None
            await msg.edit(embed=self.build_now_playing_embed(guild), view=view)
        except:
            pass

    async def post_queue_ended_new_embed(self, guild: discord.Guild):
        st = self.get_state(guild.id)
        ch = guild.get_channel(st.last_play_text_channel_id) if st.last_play_text_channel_id else None
        if isinstance(ch, discord.TextChannel):
            try:
                await ch.send(embed=self.build_queue_ended_embed(guild))
            except:
                pass

        st.panel_channel_id = None
        st.panel_message_id = None

    def _hit_cooldown(self, guild_id: int):
        st = self.get_state(guild_id)
        st.cooldown_until = time.monotonic() + 1.0

    def _ensure_player_loop_running(self, guild: discord.Guild, player: wavelink.Player):
        """If bot is connected but idle, ensure player_loop task is running (fix: VC idle /play no sound)."""
        st = self.get_state(guild.id)

        # if task missing/done -> start
        if (not st.player_task) or st.player_task.done():
            st.player_task = self.bot.loop.create_task(self.player_loop(guild.id))
            return

        # task exists but bot is idle & no current -> might be stuck from older run, restart
        if st.current is None and not getattr(player, "playing", False) and not getattr(player, "paused", False):
            try:
                st.player_task.cancel()
            except:
                pass
            st.player_task = self.bot.loop.create_task(self.player_loop(guild.id))

    async def player_loop(self, guild_id: int):
        st = self.get_state(guild_id)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        while True:
            player = self.get_player(guild)
            if not player or not getattr(player, "connected", False):
                return

            if st.stopped:
                st.stopped = False
                st.current = None
                st.loop_enabled = False
                while not st.queue.empty():
                    try:
                        st.queue.get_nowait()
                    except:
                        break

                try:
                    await player.stop()
                except:
                    pass
                try:
                    await player.disconnect()
                except:
                    pass

                st.panel_channel_id = None
                st.panel_message_id = None
                return

            try:
                track = await asyncio.wait_for(st.queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                if st.current is None and st.queue.empty() and not getattr(player, "playing", False) and not getattr(player, "paused", False):
                    return
                continue

            while True:
                st.current = track
                try:
                    await player.play(track.playable)
                except Exception as e:
                    print("❌ player.play failed:", e)
                    traceback.print_exc()
                    st.current = None
                
                    if not st.queue.empty():
                        try:
                            track = st.queue.get_nowait()
                            continue
                        except:
                            pass
                    break

                await asyncio.sleep(0.25)
                await self.apply_filters(guild)

                try:
                    await self.refresh_panel(guild, keep_buttons=True)
                except:
                    pass

                while getattr(player, "playing", False) or getattr(player, "paused", False):
                    if st.stopped:
                        try:
                            await player.stop()
                        except:
                            pass
                        break
                    await asyncio.sleep(0.75)

                if st.stopped:
                    st.current = None
                    break

                if st.loop_enabled:
                    continue

                st.current = None
                break

            if st.queue.empty() and not st.stopped and not st.loop_enabled:
                msg = await self.get_panel_message(guild)
                if msg:
                    try:
                        await msg.edit(embed=self.build_queue_ended_embed(guild), view=None)
                    except:
                        pass

                await self.post_queue_ended_new_embed(guild)
                await asyncio.sleep(600)
                if not st.queue.empty() or getattr(player, "playing", False) or getattr(player, "paused", False):
                    continue
                ch = guild.get_channel(st.last_play_text_channel_id) if st.last_play_text_channel_id else None
                if isinstance(ch, discord.TextChannel):
                    try:
                        await ch.send(embed=build_idle_leave_embed(self, guild))
                    except:
                        pass
                try:
                    await player.disconnect()
                except:
                    pass
                st.current = None
                return

    # ---------- buttons ----------
    async def _btn_play(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "paused", False):
            try:
                await player.pause(False)
            except:
                try:
                    await player.resume()
                except:
                    pass
            await interaction.followup.send("▶️ Resumed.", ephemeral=True)
        else:
            await interaction.followup.send("Already playing.", ephemeral=True)

        await self.refresh_panel(guild, keep_buttons=True)

    async def _btn_pause(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "playing", False) and not getattr(player, "paused", False):
            try:
                await player.pause(True)
            except:
                try:
                    await player.pause()
                except:
                    pass
            await interaction.followup.send("⏸️ Paused.", ephemeral=True)
        else:
            await interaction.followup.send("Nothing is playing.", ephemeral=True)

        await self.refresh_panel(guild, keep_buttons=True)

    async def _btn_skip(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        st = self.get_state(guild.id)
        st.loop_enabled = False

        player = self.get_player(guild)
        if not player or not getattr(player, "connected", False):
            return await interaction.followup.send("Not connected.", ephemeral=True)

        if getattr(player, "playing", False) or getattr(player, "paused", False):
            try:
                await player.stop()
            except:
                pass
            await interaction.followup.send("⏭️ Skipped.", ephemeral=True)
        else:
            await interaction.followup.send("Nothing to skip.", ephemeral=True)

        if st.queue.empty() and st.current is None:
            msg = await self.get_panel_message(guild)
            if msg:
                try:
                    await msg.edit(embed=self.build_queue_ended_embed(guild), view=None)
                except:
                    pass
            await self.post_queue_ended_new_embed(guild)
        else:
            await self.refresh_panel(guild, keep_buttons=True)

    async def _btn_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        st = self.get_state(guild.id)
        st.stopped = True
        st.loop_enabled = False

        player = self.get_player(guild)
        if player and getattr(player, "connected", False):
            try:
                await player.stop()
            except:
                pass
            try:
                await player.disconnect()
            except:
                pass

        while not st.queue.empty():
            try:
                st.queue.get_nowait()
            except:
                break
        st.current = None

        msg = await self.get_panel_message(guild)
        if msg:
            try:
                await msg.edit(embed=self.build_queue_ended_embed(guild), view=None)
            except:
                pass
        st.panel_channel_id = None
        st.panel_message_id = None

        await interaction.followup.send("⏹️ Stopped.", ephemeral=True)

    async def _btn_8d(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        st = self.get_state(guild.id)
        st.eightd_enabled = not st.eightd_enabled
        await self.apply_filters(guild)

        await interaction.followup.send(f"♾️ 8D: {'On' if st.eightd_enabled else 'Off'}", ephemeral=True)
        await self.refresh_panel(guild, keep_buttons=True)

    async def _btn_loop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        self._hit_cooldown(guild.id)

        st = self.get_state(guild.id)
        st.loop_enabled = not st.loop_enabled

        await interaction.followup.send(f"🔁 Loop: {'On' if st.loop_enabled else 'Off'}", ephemeral=True)
        await self.refresh_panel(guild, keep_buttons=True)

    # ---------- SLASH COMMANDS (ONLY /play and /stop) ----------
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

        if isinstance(interaction.channel, discord.TextChannel):
            st.last_play_text_channel_id = interaction.channel.id

        try:
            if query.startswith("http://") or query.startswith("https://"):
                results = await wavelink.Playable.search(query)
            else:
                results = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)

            playables: list[wavelink.Playable] = []

            if results is None:
                playables = []
            elif isinstance(results, wavelink.Playlist):
                playables = list(results)
            elif isinstance(results, (list, tuple)):
                playables = list(results[:3])
            else:
                playables = [results]

            if not playables:
                return await interaction.edit_original_response(
                    content="No tracks found. (Make sure Lavalink YouTube plugin is enabled.)"
                )

            if st.stopped:
                st.stopped = False

            for p in playables:
                await st.queue.put(Track(playable=p, requester_id=interaction.user.id))
            
            self._ensure_player_loop_running(guild, player)
            await asyncio.sleep(0.15)
            
            if isinstance(interaction.channel, discord.TextChannel):
                await self.set_panel(
                    interaction.channel,
                    guild,
                    embed=self.build_now_playing_embed(guild),
                    view=MusicPanelView(self, guild.id),
                )
            await interaction.edit_original_response(content=f"Queued: {st.queue.qsize()} track(s).")
            
            try:
                await self.refresh_panel(guild, keep_buttons=True)
            except:
                pass

        except Exception as e:
            print("❌ /play failed:", e)
            traceback.print_exc()
            await interaction.edit_original_response(content=f"Play failed: {e}")

    @app_commands.command(name="stop", description="Stop playback and clear queue (same VC only)")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):

        if not await self._ensure_same_vc(interaction):
            return

        await self._btn_stop(interaction)

    # ---------- events ----------
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._node_ready.is_set():
            try:
                await self._connect_node()
            except Exception as e:
                print("❌ Lavalink node connect failed:", e)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        try:
            st = self.states.pop(guild.id, None)
            self._voice_locks.pop(guild.id, None)
            if st and st.player_task and not st.player_task.done():
                st.stopped = True
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))