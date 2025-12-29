import discord
from discord.ext import commands
import wavelink

class JoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER ONLY (AUTO DETECT) ----------
    async def cog_check(self, ctx: commands.Context):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            await ctx.send("Only the server owner can use this command.")
            return False
        return True

    # ---------------- JOIN VC (24/7) ----------------
    @commands.command(name="joinvc")
    async def joinvc(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("Invalid voice channel ID.")

        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(cls=wavelink.Player)

        await ctx.send(
            f"Bot has joined {channel.name} and will stay connected 24/7."
        )

    # ---------------- LEAVE VC ----------------
    @commands.command(name="leavevc")
    async def leavevc(self, ctx):
        if not ctx.voice_client:
            return await ctx.send("The bot is not connected to any voice channel.")

        await ctx.voice_client.disconnect()
        await ctx.send("Bot has left the voice channel.")

async def setup(bot):
    await bot.add_cog(JoinLeave(bot))
