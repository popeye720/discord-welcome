import discord
from discord.ext import commands
from datetime import datetime


class ServerProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔐 ADMIN / OWNER CHECK
    def admin_or_owner():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    @commands.command(name="serverprofile")
    @admin_or_owner()
    async def serverprofile(self, ctx):

        guild = ctx.guild

        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        embed = discord.Embed(
            title="🏠 Server Profile",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(
            name="Owner",
            value=guild.owner.mention if guild.owner else "Unknown",
            inline=True
        )

        embed.add_field(
            name="Created On",
            value=guild.created_at.strftime("%d %b %Y"),
            inline=True
        )

        embed.add_field(
            name="Members",
            value=f"👤 {humans} | 🤖 {bots}",
            inline=True
        )

        embed.add_field(
            name="Boosts",
            value=f"Level {guild.premium_tier} ({guild.premium_subscription_count})",
            inline=True
        )

        embed.add_field(
            name="Channels",
            value=f"💬 {text_channels} | 🔊 {voice_channels} | 📁 {categories}",
            inline=True
        )

        embed.add_field(
            name="Roles",
            value=len(guild.roles),
            inline=True
        )

        embed.set_footer(
            text="TEJAS • One bot. Infinite possibilities."
        )

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerProfile(bot))
