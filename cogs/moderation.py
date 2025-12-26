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

    # ---------- EMBED BUILDER ----------
    def dm_embed(self, title, description, guild, color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text=f"Server: {guild.name}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    # ---------------- KICK ----------------
    @commands.command()
    async def kick(self, ctx, member: discord.Member = None, *, reason="No reason provided"):
        if not member:
            return await ctx.send("❌ Usage: `!kick @user reason`")

        # DM Embed
        try:
            embed = self.dm_embed(
                "👢 You were kicked",
                f"**Reason:** {reason}",
                ctx.guild,
                discord.Color.orange()
            )
            await member.send(embed=embed)
        except:
            pass

        await member.kick(reason=reason)
        await ctx.send(f"✅ **{member}** has been kicked.")

    # ---------------- BAN ----------------
    @commands.command()
    async def ban(self, ctx, member: discord.Member = None, *, reason="No reason provided"):
        if not member:
            return await ctx.send("❌ Usage: `!ban @user reason`")

        # DM Embed
        try:
            embed = self.dm_embed(
                "🔨 You were banned",
                f"**Reason:** {reason}",
                ctx.guild,
                discord.Color.red()
            )
            await member.send(embed=embed)
        except:
            pass

        await member.ban(reason=reason)
        await ctx.send(f"✅ **{member}** has been banned.")

    # ---------------- TIMEOUT ----------------
    @commands.command()
    async def timeout(self, ctx, member: discord.Member = None, minutes: int = None, *, reason="No reason provided"):
        if not member or not minutes:
            return await ctx.send("❌ Usage: `!timeout @user 5 reason`")

        duration = timedelta(minutes=minutes)

        # DM Embed
        try:
            embed = self.dm_embed(
                "⏳ You were timed out",
                f"**Duration:** {minutes} minutes\n**Reason:** {reason}",
                ctx.guild,
                discord.Color.yellow()
            )
            await member.send(embed=embed)
        except:
            pass

        await member.timeout(duration, reason=reason)
        await ctx.send(f"⏳ **{member}** timed out for **{minutes} minutes**.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
