import discord
from discord.ext import commands
import wavelink

# ================= MUSIC CONTROLS =================

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player
        self.loop = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.voice is not None

    @discord.ui.button(label="Pause", emoji="⏸️")
    async def pause(self, interaction, button):
        await self.player.pause(True)
        await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, interaction, button):
        await self.player.pause(False)
        await interaction.response.send_message("▶️ Resumed", ephemeral=True)

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

    @commands.command()
    async def play(self, ctx, *, search: str):

        if not await self.ensure_voice(ctx):
            return

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        # ✅ CORRECT SEARCH (NO PREFIX)
        tracks = await wavelink.Playable.search(search)

        if not tracks:
            return await ctx.send("❌ No results found")

        track = tracks[0]

        if player.playing:
            player.queue.put(track)
            await ctx.send(f"📥 Queued: **{track.title}**")
        else:
            await player.play(track)
            await ctx.send(
                f"🎶 Now Playing: **{track.title}**",
                view=MusicControls(player)
            )

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("⏹️ Stopped & left VC")

async def setup(bot):
    await bot.add_cog(Music(bot))
