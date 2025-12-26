import discord
from discord.ext import commands
import wavelink
import os

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class JoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.owner_locked = False  # 🔒 default

    # ---------- OWNER ONLY ----------
    async def cog_check(self, ctx: commands.Context):
        if ctx.author.id != OWNER_ID:
            await ctx.send("🚫 This command is **Owner Only**.")
            return False
        return True

    # ---------------- JOIN ----------------
    @commands.command()
    async def join(self, ctx, channel_id: int = None):

        if channel_id is None:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.send("❌ You must be in a voice channel.")
            channel = ctx.author.voice.channel
        else:
            channel = ctx.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                return await ctx.send("❌ Invalid voice channel ID.")

        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(cls=wavelink.Player)

        # 🔒 LOCK MUSIC FOR OWNER ONLY
        self.bot.owner_locked = True

        await ctx.send(f"🔒 Joined **{channel.name}** (Music locked for OWNER only)")

    # ---------------- LEAVE ----------------
    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

        # 🔓 UNLOCK MUSIC
        self.bot.owner_locked = False

        await ctx.send("👋 Left voice channel (Music unlocked)")

async def setup(bot):
    await bot.add_cog(JoinLeave(bot))
