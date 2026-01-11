import discord
from discord.ext import commands
from discord import app_commands


class JoinLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK -----------------
    def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # ----------------- GET VC SAFELY (PER GUILD) -----------------
    def get_voice_client(self, guild: discord.Guild):
        for vc in self.bot.voice_clients:
            if vc.guild.id == guild.id:
                return vc
        return None

    # ----------------- JOIN VC -----------------
    @app_commands.command(
        name="join",
        description="Make the bot join a voice channel"
    )
    async def joinvc(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel
    ):
        if not self.is_admin_or_owner(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            vc = self.get_voice_client(interaction.guild)

            if vc and vc.is_connected():
                await vc.move_to(channel)
            else:
                await channel.connect(self_deaf=True)

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
        if not self.is_admin_or_owner(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        vc = self.get_voice_client(interaction.guild)

        if not vc or not vc.is_connected():
            await interaction.edit_original_response(
                content="❌ Bot is not connected to any VC in this server."
            )
            return

        try:
            await vc.disconnect()

            await interaction.edit_original_response(
                content="✅ Left the voice channel"
            )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Failed to leave VC\n`{e}`"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
