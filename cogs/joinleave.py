import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class JoinLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Helper: Permission Check
    def has_permissions(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        return (
            interaction.user.id == interaction.guild.owner_id 
            or interaction.user.guild_permissions.administrator
        )

    @app_commands.command(
        name="join",
        description="Make the bot join a voice channel"
    )
    @app_commands.describe(channel="The voice channel to join (optional if you are in one)")
    async def join(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None
    ):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ You lack Administrator permissions.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Determine target channel: specified channel OR user's current channel
        target_channel = channel or (interaction.user.voice.channel if interaction.user.voice else None)

        if not target_channel:
            return await interaction.edit_original_response(
                content="❌ Please specify a channel or join one yourself first."
            )

        try:
            # interaction.guild.voice_client is the cleanest way to get the bot's VC in that server
            vc = interaction.guild.voice_client

            if vc:
                await vc.move_to(target_channel)
            else:
                await target_channel.connect(self_deaf=True)

            await interaction.edit_original_response(content=f"✅ Joined **{target_channel.name}**")
        
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error: `{e}`")

    @app_commands.command(
        name="leave",
        description="Disconnect the bot from voice"
    )
    async def leave(self, interaction: discord.Interaction):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ You lack Administrator permissions.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.edit_original_response(content="❌ I am not connected to any voice channel.")

        await vc.disconnect()
        await interaction.edit_original_response(content="✅ Successfully disconnected.")

async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
