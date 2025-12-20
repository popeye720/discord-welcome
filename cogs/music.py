import discord
from discord.ext import commands
import wavelink

# ================= BUTTON VIEW =================

class MusicControls(discord.ui.View):
    def __init__(self, ctx: commands.Context, player: wavelink.Player):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player
        self.loop = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ Pehle voice channel join karo", ephemeral=True
            )
            return False
        return True

    # ⏸️ PAUSE
    @discord.ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    # ▶️ RESUME
    @discord.ui.button(label="Resume", emoji="▶️", style=discord.ButtonStyle.secondary)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    # ⏭️ SKIP
    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    # 🔁 LOOP
    @discord.ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.success)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.loop = not self.loop
        self.player.queue.loop = self.loop
        state = "ON" if self.loop else "OFF"
        await interaction.response.send_message(f"🔁 Loop **{state}**", ephemeral=True)

    # ⏹️ STOP
    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        await interaction.response.send_message("⏹️ Stopped & left VC", ephemeral=True)
        self.stop()

# ================= MUSIC COG =================

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Pehle voice channel join karo")
            return False
        return True

    # ▶️ PLAY (QUEUE SAFE)
    @commands.command()
    async def play(self, ctx, *, search: str):
        if not await self.ensure_voice(ctx):
            return

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send("❌ No results found")

        track = tracks[0]

        if player.playing or player.paused:
            player.queue.put(track)
            await ctx.send(f"📥 **Queued:** {track.title}")
        else:
            await player.play(track)
            await self.send_now_playing(ctx, player, track)

    async def send_now_playing(self, ctx, player, track):
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.green()
        )
        view = MusicControls(ctx, player)
        await ctx.send(embed=embed, view=view)

    # 🎵 AUTO PLAY NEXT SONG
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player

        if player.queue.loop:
            await player.play(payload.track)
            return

        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)

    # 📜 QUEUE
    @commands.command()
    async def queue(self, ctx):
        player: wavelink.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.send("📭 Queue empty hai")

        desc = "\n".join(
            f"{i+1}. {track.title}"
            for i, track in enumerate(player.queue)
        )

        embed = discord.Embed(
            title="📜 Music Queue",
            description=desc,
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    # ⏹️ STOP (COMMAND)
    @commands.command()
    async def stop(self, ctx):
        player = ctx.voice_client
        if player:
            await player.disconnect()
            await ctx.send("⏹️ Stopped & left")

async def setup(bot):
    await bot.add_cog(Music(bot))
