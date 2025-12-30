import discord
from discord.ext import commands

from database.models import autorole_col


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------- MEMBER JOIN ----------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = autorole_col.find_one({"guild_id": member.guild.id})
        if not data:
            return

        for role_id in data.get("role_ids", []):
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto role on join")
                except Exception:
                    pass

    # ---------- ADD AUTOROLE ----------
    @commands.command(name="autorole")
    async def add_autorole(self, ctx, role_id: int):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **server owner** can use this command.")

        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send("❌ Invalid role ID.")

        data = autorole_col.find_one({"guild_id": ctx.guild.id})
        if data and role_id in data.get("role_ids", []):
            return await ctx.send(
                f"⚠️ **{role.name}** is already added as an auto role."
            )

        autorole_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$addToSet": {"role_ids": role_id}},
            upsert=True
        )

        await ctx.send(f"✅ Auto role added: **{role.name}**")

    # ---------- REMOVE AUTOROLE ----------
    @commands.command(name="removeautorole")
    async def remove_autorole(self, ctx, role_id: int):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **server owner** can use this command.")

        data = autorole_col.find_one({"guild_id": ctx.guild.id})
        if not data or role_id not in data.get("role_ids", []):
            return await ctx.send("⚠️ This role is not in the auto-role list.")

        autorole_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$pull": {"role_ids": role_id}}
        )

        role = ctx.guild.get_role(role_id)
        await ctx.send(
            f"❌ Auto role removed: **{role.name if role else role_id}**"
        )

    # ---------- LIST AUTOROLES ----------
    @commands.command(name="autorolelist")
    async def autorole_list(self, ctx):
        data = autorole_col.find_one({"guild_id": ctx.guild.id})
        if not data or not data.get("role_ids"):
            return await ctx.send("ℹ️ No auto roles are set for this server.")

        roles = []
        for role_id in data["role_ids"]:
            role = ctx.guild.get_role(role_id)
            if role:
                roles.append(role.mention)

        embed = discord.Embed(
            title="📜 Auto Roles List",
            description="\n".join(roles),
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

    # ---------- CLEAR ALL ----------
    @commands.command(name="clearautoroles")
    async def clear_autoroles(self, ctx):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **server owner** can use this command.")

        autorole_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.send("🗑️ All auto roles have been cleared.")


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
