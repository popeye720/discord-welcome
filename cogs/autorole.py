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

    # -------- ADD AUTOROLE --------
    @commands.command(name="autorole")
    @is_admin()
    async def autorole(self, ctx, role_id: int):
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.reply("❌ Invalid role ID")

        if role >= ctx.guild.me.top_role:
            return await ctx.reply("❌ I can't assign this role.")

        # ❌ prevent duplicate
        existing = autorole_col.find_one({
            "guild_id": ctx.guild.id,
            "role_id": role_id
        })
        if existing:
            return await ctx.reply("⚠️ This autorole already exists.")

        autorole_col.insert_one({
            "guild_id": ctx.guild.id,
            "role_id": role_id
        })

        await ctx.reply(f"✅ Auto role **{role.name}** added.")

    # -------- CANCEL AUTOROLE --------
    @commands.command(name="autorolecancel")
    @is_admin()
    async def autorole_cancel(self, ctx, role_id: int = None):
        if role_id:
            result = autorole_col.find_one_and_delete({
                "guild_id": ctx.guild.id,
                "role_id": role_id
            })

            if not result:
                return await ctx.reply("❌ This autorole does not exist.")

            role = ctx.guild.get_role(role_id)
            name = role.name if role else str(role_id)

            return await ctx.reply(f"✅ Autorole **{name}** removed.")

        # 🔥 no role_id → delete all
        result = autorole_col.delete_many({
            "guild_id": ctx.guild.id
        })

        if result.deleted_count == 0:
            return await ctx.reply("❌ No autoroles are set.")

        await ctx.reply("✅ All autoroles removed.")

    # -------- LIST AUTOROLES --------
    @commands.command(name="autorolelist")
    @is_admin()
    async def autorole_list(self, ctx):
        roles = autorole_col.find(
            {"guild_id": ctx.guild.id}
        )

        role_mentions = []
        for r in roles:
            role = ctx.guild.get_role(r["role_id"])
            if role:
                role_mentions.append(role.mention)

        if not role_mentions:
            return await ctx.reply("❌ No autoroles set.")

        text = "\n".join(role_mentions)

        embed = discord.Embed(
            title="Auto Roles",
            description=text,
            color=discord.Color.blurple()
        )

        await ctx.reply(embed=embed)

    # -------- GIVE AUTOROLES ON JOIN --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        roles = autorole_col.find({
            "guild_id": member.guild.id
        })

        for r in roles:
            role = member.guild.get_role(r["role_id"])
            if not role:
                continue

            if role >= member.guild.me.top_role:
                continue

            try:
                await member.add_roles(role, reason="Auto Role")
            except (discord.Forbidden, discord.HTTPException):
                continue


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
