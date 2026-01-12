import discord
from discord.ext import commands
from discord import app_commands

from database.models import privatevc_col


class PrivateVC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================== PERMISSION CHECK ==================
    def is_admin_owner_or_role(self, interaction, role_id):
        if interaction.user.id == interaction.guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        if role_id and discord.utils.get(interaction.user.roles, id=role_id):
            return True
        return False

    # ================== /privatevcsetup ==================
    @app_commands.command(name="privatevcsetup")
    async def privatevcsetup(self, interaction: discord.Interaction, role: discord.Role):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

        privatevc_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "enabled": True,
                    "allowed_role_id": role.id,
                    "active_vcs": {}
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Private VC system enabled\nAllowed role: {role.mention}",
            ephemeral=True
        )

    # ================== /privatevccreate ==================
    @app_commands.command(name="privatevccreate")
    async def privatevc(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        data = privatevc_col.find_one({"guild_id": guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message("❌ System disabled.", ephemeral=True)

        if not self.is_admin_owner_or_role(interaction, data.get("allowed_role_id")):
            return await interaction.response.send_message("❌ Not allowed.", ephemeral=True)

        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message("❌ Join a VC first.", ephemeral=True)

        if str(user.id) in data.get("active_vcs", {}):
            return await interaction.response.send_message(
                "❌ You already have a private VC.", ephemeral=True
            )

        base_vc = user.voice.channel
        members = base_vc.members

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True)
        }

        vc = await guild.create_voice_channel(
            name=f"{user.name}'s Private VC",
            category=base_vc.category,
            overwrites=overwrites
        )

        for m in members:
            await m.move_to(vc)

        privatevc_col.update_one(
            {"guild_id": guild.id},
            {
                "$set": {
                    f"active_vcs.{user.id}": {
                        "channel_id": vc.id,
                        "owner_id": user.id,
                        "allowed_users": []
                    }
                }
            }
        )

        await interaction.response.send_message("✅ Private VC created.", ephemeral=True)

    # ================== /privatevcallow ==================
    @app_commands.command(name="privatevcallow")
    async def privatevcallow(self, interaction: discord.Interaction, user: discord.Member):
        data = privatevc_col.find_one({"guild_id": interaction.guild.id})
        vc_data = data.get("active_vcs", {}).get(str(interaction.user.id))

        if not vc_data:
            return await interaction.response.send_message("❌ You don't own a VC.", ephemeral=True)

        vc = interaction.guild.get_channel(vc_data["channel_id"])
        if vc:
            await vc.set_permissions(user, view_channel=True, connect=True, speak=True)

        privatevc_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": {f"active_vcs.{interaction.user.id}.allowed_users": user.id}}
        )

        await interaction.response.send_message("✅ User allowed.", ephemeral=True)

    # ================== /privatevcremove ==================
    @app_commands.command(name="privatevcremove")
    async def privatevcremove(self, interaction: discord.Interaction, user: discord.Member):
        data = privatevc_col.find_one({"guild_id": interaction.guild.id})
        vc_data = data.get("active_vcs", {}).get(str(interaction.user.id))

        if not vc_data:
            return await interaction.response.send_message("❌ You don't own a VC.", ephemeral=True)

        vc = interaction.guild.get_channel(vc_data["channel_id"])
        if vc:
            if user.voice and user.voice.channel == vc:
                await user.move_to(None)
            await vc.set_permissions(user, view_channel=False, connect=False)

        await interaction.response.send_message("🚫 User removed.", ephemeral=True)

    # ================== AUTO DELETE IF OWNER LEAVES ==================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and before.channel != after.channel:
            data = privatevc_col.find_one({"guild_id": member.guild.id})
            vc_data = data.get("active_vcs", {}).get(str(member.id))

            if vc_data and before.channel.id == vc_data["channel_id"]:
                for m in before.channel.members:
                    await m.move_to(None)
                await before.channel.delete()

                privatevc_col.update_one(
                    {"guild_id": member.guild.id},
                    {"$unset": {f"active_vcs.{member.id}": ""}}
                )


async def setup(bot):
    await bot.add_cog(PrivateVC(bot))
