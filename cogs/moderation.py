import discord
from discord.ext import commands
from datetime import timedelta


class OwnerModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER + ADMIN CHECK ----------
    async def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            return False

        if (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return True

        await ctx.send(
            "You do not have permission to use this command."
        )
        return False

    # ---------- DM EMBED BUILDER ----------
    def dm_embed(
        self,
        title: str,
        description: str,
        guild: discord.Guild,
        color: discord.Color
    ):
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
    async def kick(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = "No reason provided"
    ):
        if not member:
            return await ctx.send("Usage: !kick @user <reason>")

        try:
            embed = self.dm_embed(
                "You were kicked from the server",
                f"Reason: {reason}",
                ctx.guild,
                discord.Color.orange()
            )
            await member.send(embed=embed)
        except Exception:
            pass

        await member.kick(reason=reason)
        await ctx.send(f"{member} has been kicked.")

    # ---------------- BAN ----------------
    @commands.command()
    async def ban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = "No reason provided"
    ):
        if not member:
            return await ctx.send("Usage: !ban @user <reason>")

        try:
            embed = self.dm_embed(
                "You were banned from the server",
                f"Reason: {reason}",
                ctx.guild,
                discord.Color.red()
            )
            await member.send(embed=embed)
        except Exception:
            pass

        await member.ban(reason=reason)
        await ctx.send(f"{member} has been banned.")

    # ---------------- TIMEOUT ----------------
    @commands.command()
    async def timeout(
        self,
        ctx,
        member: discord.Member = None,
        minutes: int = None,
        *,
        reason: str = "No reason provided"
    ):
        if not member or not minutes:
            return await ctx.send("Usage: !timeout @user <minutes> <reason>")

        duration = timedelta(minutes=minutes)

        try:
            embed = self.dm_embed(
                "You were temporarily timed out",
                f"Duration: {minutes} minutes\nReason: {reason}",
                ctx.guild,
                discord.Color.yellow()
            )
            await member.send(embed=embed)
        except Exception:
            pass

        await member.timeout(duration, reason=reason)
        await ctx.send(
            f"{member} has been timed out for {minutes} minutes."
        )


async def setup(bot):
    await bot.add_cog(OwnerModeration(bot))
