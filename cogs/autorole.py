from discord.ext import commands
import discord

from database.models import autorole_col


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- PERMISSION CHECK (ADMIN / OWNER) --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SET AUTOROLE --------
    @commands.command(name="autorole")
    @is_admin()
    async def set_autorole(self, ctx, role_id: int):
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.reply("❌ Invalid role ID")

        # bot permission check
        if role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "❌ I don't have permission to assign this role."
            )

        autorole_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"role_id": role_id}},
            upsert=True
        )

        await ctx.reply(f"✅ Auto role set to **{role.name}**")

    # -------- AUTO GIVE ROLE ON JOIN --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = autorole_col.find_one(
            {"guild_id": member.guild.id}
        )

        if not data:
            return

        role = member.guild.get_role(data["role_id"])
        if not role:
            return

        # safety check
        if role >= member.guild.me.top_role:
            return

        try:
            await member.add_roles(role, reason="Auto Role")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
