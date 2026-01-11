import discord
from discord.ext import commands
from discord import app_commands
from database.models import autorole_col
import asyncio


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ----------------- ADD AUTOROLE -----------------
    @app_commands.command(name="autorole", description="Add an auto role")
    async def autorole(self, interaction: discord.Interaction, role: discord.Role):
        if not await self.is_admin_or_owner(interaction):
            return

        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "❌ I can't assign this role.",
                ephemeral=True
            )

        # 🔒 DUPLICATE CHECK
        existing = autorole_col.find_one({
            "guild_id": interaction.guild.id,
            "role_id": role.id
        })
        if existing:
            return await interaction.response.send_message(
                "⚠️ This autorole already exists.",
                ephemeral=True
            )

        autorole_col.insert_one({
            "guild_id": interaction.guild.id,
            "role_id": role.id
        })

        await interaction.response.send_message(
            f"✅ Auto role **{role.name}** added.",
            ephemeral=True
        )

    # ----------------- CANCEL AUTOROLE -----------------
    @app_commands.command(name="autorolecancel", description="Remove an auto role")
    async def autorole_cancel(self, interaction: discord.Interaction, role: discord.Role = None):
        if not await self.is_admin_or_owner(interaction):
            return

        if role:
            result = autorole_col.find_one_and_delete({
                "guild_id": interaction.guild.id,
                "role_id": role.id
            })

            if not result:
                return await interaction.response.send_message(
                    "❌ This autorole does not exist.",
                    ephemeral=True
                )

            await interaction.response.send_message(
                f"✅ Autorole **{role.name}** removed.",
                ephemeral=True
            )
            return

        # 🔥 No role → delete all
        result = autorole_col.delete_many({"guild_id": interaction.guild.id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "❌ No autoroles are set.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "✅ All autoroles removed.",
            ephemeral=True
        )

    # ----------------- LIST AUTOROLES -----------------
    @app_commands.command(name="autorolelist", description="List all auto roles")
    async def autorole_list(self, interaction: discord.Interaction):
        roles_data = autorole_col.find({"guild_id": interaction.guild.id})

        role_mentions = []
        for r in roles_data:
            role = interaction.guild.get_role(r["role_id"])
            if role:
                role_mentions.append(role.mention)

        if not role_mentions:
            return await interaction.response.send_message(
                "❌ No autoroles set.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="Auto Roles",
            description="\n".join(role_mentions),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- GIVE AUTOROLES ON JOIN -----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        roles_data = autorole_col.find({"guild_id": member.guild.id})

        for r in roles_data:
            role = member.guild.get_role(r["role_id"])
            if not role:
                continue
            if role >= member.guild.me.top_role:
                continue
            try:
                await member.add_roles(role, reason="Auto Role")
            except (discord.Forbidden, discord.HTTPException):
                continue

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))
