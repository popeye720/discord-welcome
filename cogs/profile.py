import discord
from discord.ext import commands
from datetime import datetime


class Profile(commands.Cog):
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

    @commands.command(name="profile")
    @admin_or_owner()
    async def profile(self, ctx, user: str = None):

        if not user:
            return await ctx.reply("❌ Usage: `!profile @user` OR `!profile user_id`")

        # 🔥 Resolve mention OR ID
        member = None

        if user.isdigit():
            member = ctx.guild.get_member(int(user))
        else:
            member = ctx.message.mentions[0] if ctx.message.mentions else None

        if not member:
            return await ctx.reply("❌ User not found in this server.")

        roles = [r for r in member.roles if r.name != "@everyone"]
        top_role = roles[-1].mention if roles else "None"

        embed = discord.Embed(
            title="👤 User Profile",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%d %b %Y"),
            inline=True
        )
        embed.add_field(
            name="Joined Server",
            value=member.joined_at.strftime("%d %b %Y"),
            inline=True
        )
        embed.add_field(name="Roles Count", value=len(roles), inline=True)
        embed.add_field(name="Top Role", value=top_role, inline=True)

        embed.set_footer(text="TEJAS • One bot. Infinite possibilities.")

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Profile(bot))
