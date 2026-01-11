import discord
from discord.ext import commands
from discord import app_commands


class JoinLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction):
        guild = interaction.guild
        return (
            guild
            and (
                interaction.user.id == guild.owner_id
                or interaction.user.guild_permissions.administrator
            )
        )

    # ----------------- JOIN VC -----------------
    @app_commands.command(
        name="join",
        description="Make the bot join a voice channel"
    )
    @app_commands.describe(channel="Voice channel to join")
    async def joinvc(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

        # 🔥 ACK immediately
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(channel)
            else:
                await channel.connect()

            await interaction.edit_original_response(
                content=f"✅ Joined **{channel.name}**"
            )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Failed to join VC\n`{e}`"
            )

    # ----------------- LEAVE VC -----------------
    @app_commands.command(
        name="leave",
        description="Make the bot leave voice channel"
    )
    async def leavevc(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message(
                "❌ Bot is not connected to a voice channel.",
                ephemeral=True
            )

        # 🔥 ACK immediately
        await interaction.response.defer(ephemeral=True)

        try:
            await vc.disconnect(force=True)  # ⚡ immediate leave

            await interaction.edit_original_response(
                content="✅ Left the voice channel"
            )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Failed to leave VC\n`{e}`"
            )

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
