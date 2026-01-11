import discord
from discord.ext import commands
from discord import app_commands


class JoinLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------- PERMISSION CHECK (NO RESPONSE HERE) --------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # -------- JOIN VOICE CHANNEL --------
    @app_commands.command(
        name="joinvc",
        description="Join a voice channel using channel ID"
    )
    async def joinvc(
        self,
        interaction: discord.Interaction,
        channel_id: int
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            return await interaction.response.send_message(
                "❌ Invalid voice channel ID.",
                ephemeral=True
            )

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        await interaction.response.send_message(
            f"✅ Joined voice channel: **{channel.name}**",
            ephemeral=True
        )

    # -------- LEAVE VOICE CHANNEL --------
    @app_commands.command(
        name="leavevc",
        description="Leave the current voice channel"
    )
    async def leavevc(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True
            )

        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.response.send_message(
                "❌ Bot is not connected to any voice channel.",
                ephemeral=True
            )

        await vc.disconnect()
        await interaction.response.send_message(
            "✅ Disconnected from the voice channel.",
            ephemeral=True
        )


# -------- SETUP --------
async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
    print("✅ JoinLeave cog loaded")    