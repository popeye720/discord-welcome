import discord
from discord.ext import commands
from datetime import timedelta


class OwnerModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- PERMISSION CHECK ----------
    def is_owner(self, ctx):
        return ctx.author.id == ctx.guild.owner_id

    def is_admin(self, member: discord.Member):
        return member.guild_permissions.administrator

    # ---------- PUNISH ADMIN ----------
    async def punish_admin(self, admin: discord.Member, guild: discord.Guild):
        try:
            await admin.timeout(
                timedelta(minutes=1),
                reason="Tried to moderate the server owner"
            )
        except:
            pass

        try:
            await admin.send("baap se panga?")
        except:
            pass

    # ---------- KICK ----------
    @commands.command()
    @commands.guild_only()
    async def kick(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = "No reason provided"
    ):
        if not member:
            return await ctx.send("Usage: !kick @user <reason>")

        # ADMIN TRYING TO TOUCH OWNER
        if (
            self.is_admin(ctx.author)
            and member.id == ctx.guild.owner_id
        ):
            await self.punish_admin(ctx.author, ctx.guild)
            return await ctx.send("❌ You cannot kick the server owner.")

        # ADMIN TRYING TO TOUCH ADMIN
        if (
            self.is_admin(ctx.author)
            and self.is_admin(member)
            and not self.is_owner(ctx)
        ):
            return await ctx.send("❌ Admins cannot kick other admins.")

        # PERMISSION CHECK
        if not (
            self.is_owner(ctx)
            or self.is_admin(ctx.author)
        ):
            return await ctx.send("❌ You do not have permission.")

        try:
            await member.send(
                f"You were kicked from **{ctx.guild.name}**\nReason: {reason}"
            )
        except:
            pass

        await member.kick(reason=reason)
        await ctx.send(f"✅ {member} has been kicked.")

    # ---------- BAN ----------
    @commands.command()
    @commands.guild_only()
    async def ban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason: str = "No reason provided"
    ):
        if not member:
            return await ctx.send("Usage: !ban @user <reason>")

        # ADMIN TRYING TO TOUCH OWNER
        if (
            self.is_admin(ctx.author)
            and member.id == ctx.guild.owner_id
        ):
            await self.punish_admin(ctx.author, ctx.guild)
            return await ctx.send("❌ You cannot ban the server owner.")

        # ADMIN TRYING TO TOUCH ADMIN
        if (
            self.is_admin(ctx.author)
            and self.is_admin(member)
            and not self.is_owner(ctx)
        ):
            return await ctx.send("❌ Admins cannot ban other admins.")

        if not (
            self.is_owner(ctx)
            or self.is_admin(ctx.author)
        ):
            return await ctx.send("❌ You do not have permission.")

        try:
            await member.send(
                f"You were banned from **{ctx.guild.name}**\nReason: {reason}"
            )
        except:
            pass

        await member.ban(reason=reason)
        await ctx.send(f"✅ {member} has been banned.")

    # ---------- TIMEOUT ----------
    @commands.command()
    @commands.guild_only()
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

        # ADMIN TRYING TO TOUCH OWNER
        if (
            self.is_admin(ctx.author)
            and member.id == ctx.guild.owner_id
        ):
            await self.punish_admin(ctx.author, ctx.guild)
            return await ctx.send("❌ You cannot timeout the server owner.")

        # ADMIN TRYING TO TOUCH ADMIN
        if (
            self.is_admin(ctx.author)
            and self.is_admin(member)
            and not self.is_owner(ctx)
        ):
            return await ctx.send("❌ Admins cannot timeout other admins.")

        if not (
            self.is_owner(ctx)
            or self.is_admin(ctx.author)
        ):
            return await ctx.send("❌ You do not have permission.")

        try:
            await member.send(
                f"You were timed out in **{ctx.guild.name}**\n"
                f"Duration: {minutes} minutes\nReason: {reason}"
            )
        except:
            pass

        await member.timeout(duration, reason=reason)
        await ctx.send(
            f"✅ {member} has been timed out for {minutes} minutes."
        )


async def setup(bot):
    await bot.add_cog(OwnerModeration(bot))
