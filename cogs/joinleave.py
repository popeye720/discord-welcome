import discord
from discord.ext import commands
import wavelink
import os

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class JoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER ONLY ----------
    async def cog_check(self, ctx: commands.Context):
        if ctx.author.id != OWNER_ID:
            await ctx.send("🚫 This command is **Owner Only**.")
            return False
        return True

    # ---------------- JOIN ----------------
    @commands.command()
    async def join(self, ctx, channel_id: int = None):
        # 🔹 Case 1: !join (no channel id)
        if channel_id is None:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.send("❌ You must be in a voice channel.")

            channel = ctx.author.voice.channel

        # 🔹 Case 2: !join <channel_id>
        else:
            channel = ctx.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                return await ctx.send("❌ Invalid voice channel ID.")

        # Join / Move
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(cls=wavelink.Player)

        await ctx.send(f"✅ Joined **{channel.name}**")

    # ---------------- LEAVE ----------------
    @commands.command()
    async def leave(self, ctx):
        if not ctx.voice_client:
            return await ctx.send("❌ I am not in any voice channel.")

        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")

async def setup(bot):
    await bot.add_cog(JoinLeave(bot))
