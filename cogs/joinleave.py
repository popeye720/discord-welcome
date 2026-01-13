import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import asyncio
import traceback

class JoinLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_permissions(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.guild
            and (
                interaction.user.id == interaction.guild.owner_id
                or interaction.user.guild_permissions.administrator
            )
        )

    @app_commands.command(name="voicejoin", description="Make the bot join a voice channel")
    @app_commands.describe(channel="Voice channel (optional)")
    async def voicejoin(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ Admin required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        target = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        if not target:
            return await interaction.edit_original_response(content="❌ Join a VC or pass channel.")

        try:
            vc = interaction.guild.voice_client
            if vc:
                await asyncio.wait_for(vc.move_to(target), timeout=10)
            else:
                await asyncio.wait_for(target.connect(self_deaf=True), timeout=10)

            return await interaction.edit_original_response(content=f"✅ Joined **{target.name}**")

        except asyncio.TimeoutError:
            return await interaction.edit_original_response(
                content="❌ Voice connect TIMEOUT (hosting/network issue)."
            )
        except Exception:
            traceback.print_exc()
            return await interaction.edit_original_response(content="❌ Voice join failed. Check logs.")

    @app_commands.command(name="voiceleave", description="Disconnect the bot from voice")
    async def voiceleave(self, interaction: discord.Interaction):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ Admin required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.edit_original_response(content="❌ Not connected.")

        await vc.disconnect()
        return await interaction.edit_original_response(content="✅ Disconnected.")

async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
