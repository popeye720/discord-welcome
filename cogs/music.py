import discord
from discord.ext import commands
import wavelink
import asyncio

# ================= MUSIC CONTROLS =================

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ Pehle VC join karo", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Pause", emoji="⏸️")
    async def pause(self, interaction, button):
        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, interaction, button):
        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="Skip", emoji="⏭️")
    async def skip(self, interaction, button):
        await self.player.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️")
    async def stop(self, interaction, button):
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

    # -------- PLAY COMMAND --------
    @commands.command()
    async def play(self, ctx, *, search: str):

        if not await self.ensure_voice(ctx):
            return

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        # ✅ SoundCloud search (stable)
        tracks = await wavelink.Playable.search(f"scsearch:{search}")

        if not tracks:
            await ctx.send("❌ Song nahi mila, VC leave kar raha hoon")
            await player.disconnect()
            return

        track = tracks[0]

        if player.playing:
            player.queue.put(track)
            await ctx.send(f"📥 **Queued:** {track.title}")
        else:
            await player.play(track)
            await ctx.send(
                f"🎶 **Now Playing:** {track.title}",
                view=MusicControls(player)
            )

    # -------- SKIP COMMAND --------
    @commands.command()
    async def skip(self, ctx):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Kuch play nahi ho raha")

        await player.stop()
        await ctx.send("⏭️ Skipped")

    # -------- QUEUE COMMAND --------
    @commands.command()
    async def queue(self, ctx):
        player: wavelink.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.send("📭 Queue empty hai")

        desc = "\n".join(
            f"{i+1}. {t.title}" for i, t in enumerate(player.queue)
        )

        embed = discord.Embed(
            title="📜 Music Queue",
            description=desc,
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    # -------- STOP COMMAND --------
    @commands.command()
    async def stop(self, ctx):
        player: wavelink.Player = ctx.voice_client
        if player:
            await player.disconnect()
            await ctx.send("⏹️ Stopped & left VC")

    # -------- AUTO LEAVE WHEN QUEUE ENDS --------
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player

        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            # ⏳ 10 sec wait, phir leave
            await asyncio.sleep(10)
            if not player.playing:
                await player.disconnect()

async def setup(bot):
    await bot.add_cog(Music(bot))
