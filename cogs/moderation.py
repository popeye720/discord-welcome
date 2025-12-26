import discord
from discord.ext import commands
from datetime import timedelta
import os

OWNER_ID = int(os.getenv("OWNER_ID", 0))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER CHECK ----------
    async def cog_check(self, ctx: commands.Context):
        if ctx.author.id != OWNER_ID:
            await ctx.send("🚫 This command is **Owner Only**.")
            return False
        return True

    # ---------------- KICK ----------------
    @commands.command()
    async def kick(self, ctx, member: discord.Member = None, *, reason="No reason provided"):
        if not member:
            return await ctx.send("❌ Usage: `!kick @user reason`")

        # DM user
        try:
            await member.send(
                f"👢 You were **kicked** from **{ctx.guild.name}**\n"
                f"📝 Reason: {reason}"
            )
        except:
            pass

        await member.kick(reason=reason)
        await ctx.send(f"✅ **{member}** has been kicked.\n📝 Reason: {reason}")

    # ---------------- BAN ----------------
    @commands.command()
    async def ban(self, ctx, member: discord.Member = None, *, reason="No reason provided"):
        if not member:
            return await ctx.send("❌ Usage: `!ban @user reason`")

        # DM user
        try:
            await member.send(
                f"🔨 You were **banned** from **{ctx.guild.name}**\n"
                f"📝 Reason: {reason}"
            )
        except:
            pass

        await member.ban(reason=reason)
        await ctx.send(f"✅ **{member}** has been banned.\n📝 Reason: {reason}")

    # ---------------- TIMEOUT ----------------
    @commands.command()
    async def timeout(self, ctx, member: discord.Member = None, minutes: int = None, *, reason="No reason provided"):
        if not member or not minutes:
            return await ctx.send("❌ Usage: `!timeout @user 5 reason`")

        duration = timedelta(minutes=minutes)

        # DM user
        try:
            await member.send(
                f"⏳ You were **timed out** in **{ctx.guild.name}**\n"
                f"⏱ Duration: {minutes} minutes\n"
                f"📝 Reason: {reason}"
            )
        except:
            pass

        await member.timeout(duration, reason=reason)
        await ctx.send(
            f"⏳ **{member}** timed out for **{minutes} minutes**.\n📝 Reason: {reason}"
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
