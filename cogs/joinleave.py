import discord
from discord.ext import commands
from discord import app_commands


class JoinLeave(commands.Cog):
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
        if not await self.is_admin_or_owner(interaction):
            return

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        await interaction.response.send_message(
            f"✅ Joined **{channel.name}**",
            ephemeral=True
        )

    # ----------------- LEAVE VC -----------------
    @app_commands.command(
        name="leave",
        description="Make the bot leave voice channel"
    )
    async def leavevc(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message(
                "❌ Bot is not connected to a voice channel.",
                ephemeral=True
            )

        await vc.disconnect()
        await interaction.response.send_message(
            "✅ Left the voice channel",
            ephemeral=True
        )

    # ----------------- GLOBAL SLASH CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
