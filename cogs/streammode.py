import discord
from discord.ext import commands
from discord import app_commands
from database.models import streammode_col


class StreamMode(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK (ADMIN / OWNER) -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # ----------------- /stream-mode -----------------
    @app_commands.command(
        name="stream-mode",
        description="Enable stream mode (blocks bots from joining your current VC)"
    )
    @app_commands.guild_only()
    async def streammode(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be connected to a voice channel.",
                ephemeral=True
            )

        vc = interaction.user.voice.channel

        if streammode_col.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "⚠️ Stream mode is already ENABLED.",
                ephemeral=True
            )

        streammode_col.insert_one({
            "guild_id": interaction.guild.id,
            "vc_id": vc.id,
            "enabled": True
        })

        await interaction.response.send_message(
            f"✅ **Stream Mode Enabled**\n"
            f"🔒 Bots are blocked from **{vc.name}**",
            ephemeral=True
        )

    # ----------------- /stream-mode-off -----------------
    @app_commands.command(
        name="stream-mode-off",
        description="Disable stream mode"
    )
    @app_commands.guild_only()
    async def streammodeoff(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        result = streammode_col.delete_one({"guild_id": interaction.guild.id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "⚠️ Stream mode is already OFF.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🟢 **Stream Mode Disabled**",
            ephemeral=True
        )

    # ----------------- /status-stream -----------------
    @app_commands.command(
        name="status-stream",
        description="Check stream mode status"
    )
    @app_commands.guild_only()
    async def statusstream(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        data = streammode_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return await interaction.response.send_message(
                "🔴 **Stream Mode:** OFF",
                ephemeral=True
            )

        vc = interaction.guild.get_channel(data["vc_id"])
        await interaction.response.send_message(
            f"🟢 **Stream Mode:** ON\n"
            f"🔒 VC: **{vc.name if vc else 'Unknown'}**",
            ephemeral=True
        )

    # ----------------- BLOCK BOTS + USER NOTICE -----------------
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        # only bots
        if not member.bot or not member.guild:
            return

        data = streammode_col.find_one({"guild_id": member.guild.id})
        if not data or not data.get("enabled"):
            return

        blocked_vc_id = data["vc_id"]

        if after.channel and after.channel.id == blocked_vc_id:
            # try to find who pulled the bot
            inviter = None
            for m in after.channel.members:
                if not m.bot and m.guild_permissions.move_members:
                    inviter = m
                    break

            # kick bot
            try:
                await member.move_to(None)
            except:
                pass

            # notify user (temporary msg)
            if inviter:
                try:
                    await after.channel.send(
                        f"🚫 {inviter.mention} **Stream Mode is enabled in this VC**\n"
                        f"🤖 Bots are not allowed here.",
                        delete_after=5
                    )
                except:
                    pass

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamMode(bot))
