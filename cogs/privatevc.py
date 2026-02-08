import discord
from discord.ext import commands
from discord import app_commands
from database.models import privatevc_col


class PrivateVC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================== USER PERMISSION ==================
    def user_allowed(self, interaction: discord.Interaction, role_id: int | None):
        user = interaction.user
        guild = interaction.guild

        if user.id == guild.owner_id:
            return True
        if user.guild_permissions.administrator:
            return True
        if role_id and discord.utils.get(user.roles, id=role_id):
            return True
        return False

    # ================== BOT PERMISSION ==================
    def bot_allowed(self, interaction: discord.Interaction):
        me = interaction.guild.me
        perms = me.guild_permissions

        return (
            perms.manage_channels
            and perms.move_members
            and perms.view_channel
            and perms.connect
        )

    # ================== GROUP ==================
    privatevc = app_commands.Group(
        name="private-vc",
        description="Private voice channel system",
        guild_only=True
    )

    # ================== SETUP ==================
    @privatevc.command(name="setup")
    async def setup_vc(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Admin only command", ephemeral=True
            )

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
            f"✅ Private VC enabled\nAllowed Role: {role.mention}",
            ephemeral=True
        )

    # ================== DISABLE ==================
    @privatevc.command(name="disable")
    async def disable_vc(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Admin only command", ephemeral=True
            )

        privatevc_col.delete_one({"guild_id": interaction.guild.id})

        await interaction.response.send_message(
            "🛑 Private VC system disabled",
            ephemeral=True
        )

    # ================== CREATE ==================
    @privatevc.command(name="create")
    async def create_vc(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        data = privatevc_col.find_one({"guild_id": guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "❌ Private VC system disabled", ephemeral=True
            )

        if not self.user_allowed(interaction, data.get("allowed_role_id")):
            return await interaction.response.send_message(
                "❌ You are not allowed to create a VC", ephemeral=True
            )

        if not self.bot_allowed(interaction):
            return await interaction.response.send_message(
                "❌ Bot missing permissions (Manage Channels / Move Members)",
                ephemeral=True
            )

        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                "❌ Join a voice channel first", ephemeral=True
            )

        if str(user.id) in data.get("active_vcs", {}):
            return await interaction.response.send_message(
                "❌ You already own a private VC", ephemeral=True
            )

        base = user.voice.channel

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True
            )
        }

        vc = await guild.create_voice_channel(
            name=f"{user.name}'s VC",
            category=base.category,
            overwrites=overwrites
        )

        for m in base.members:
            await m.move_to(vc)

        privatevc_col.update_one(
            {"guild_id": guild.id},
            {
                "$set": {
                    f"active_vcs.{user.id}": {
                        "channel_id": vc.id,
                        "owner_id": user.id
                    }
                }
            }
        )

        await interaction.response.send_message(
            f"✅ VC created: **{vc.name}**", ephemeral=True
        )

    # ================== AUTO DELETE ==================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not before.channel:
            return

        data = privatevc_col.find_one({"guild_id": member.guild.id})
        if not data:
            return

        for owner_id, vc_data in data.get("active_vcs", {}).items():
            if before.channel.id == vc_data["channel_id"]:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    privatevc_col.update_one(
                        {"guild_id": member.guild.id},
                        {"$unset": {f"active_vcs.{owner_id}": ""}}
                    )
                break


async def setup(bot: commands.Bot):
    await bot.add_cog(PrivateVC(bot))
