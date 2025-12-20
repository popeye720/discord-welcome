import discord
from discord.ext import commands
import wavelink

# ================= BUTTON VIEW =================

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player
        self.loop = False

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.playing:
            await self.player.pause()
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.paused:
            await self.player.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player:
            await self.player.stop()
            await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.success)
    async def loop_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.loop = not self.loop
        self.player.queue.loop = self.loop
        state = "ON" if self.loop else "OFF"
        await interaction.response.send_message(f"🔁 Loop **{state}**", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player:
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

    # ▶️ PLAY
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
        await player.play(track)

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.green()
        )

        view = MusicControls(player)
        await ctx.send(embed=embed, view=view)

    # ⏹️ STOP COMMAND (backup)
    @commands.command()
    async def stop(self, ctx):
        player = ctx.voice_client
        if player:
            await player.disconnect()
            await ctx.send("⏹️ Stopped & left")

async def setup(bot):
    await bot.add_cog(Music(bot))
