import discord
from discord.ext import commands


class GhostDM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 👑 OWNER + ADMIN CHECK
    def can_manage(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    @commands.command(name="ghostdm")
    async def ghostdm(self, ctx, user: str = None, *, message: str = None):

        if not self.can_manage(ctx):
            return await ctx.send("❌ Only **Server Owner or Admin** can use this command.")

        if not user or not message:
            return await ctx.send(
                "❌ Usage: `!ghostdm @user <message>` OR `!ghostdm user_id <message>`"
            )

        # 🔍 Resolve user (mention OR ID)
        member = None

        if user.isdigit():
            member = ctx.guild.get_member(int(user))
        else:
            member = ctx.message.mentions[0] if ctx.message.mentions else None

        if not member:
            return await ctx.send("❌ Invalid user or user not found in this server.")

        if member.bot:
            return await ctx.send("❌ You cannot send Ghost DM to a bot.")

        if not message.strip():
            return await ctx.send("❌ Message content cannot be empty.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.dark_purple()
        )

        # 🖼️ IMAGE → THUMB + MAIN IMAGE (same logic)
        if ctx.message.attachments:
            att = ctx.message.attachments[0]
            if att.content_type and att.content_type.startswith("image"):
                embed.set_thumbnail(url=att.url)
                embed.set_image(url=att.url)

        embed.set_footer(
            text="👻 Anonymous message via TEJAS"
        )

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            return await ctx.send("❌ Cannot send DM. User has DMs disabled.")

        await ctx.send(
            f"✅ Ghost DM sent successfully.\n"
            f"Recipient: {member.mention}"
        )


async def setup(bot):
    await bot.add_cog(GhostDM(bot))
