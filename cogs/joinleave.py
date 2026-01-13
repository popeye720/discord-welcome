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

    @app_commands.command(name="join", description="Make the bot join a voice channel (debug)")
    @app_commands.describe(channel="Voice channel (optional if you are already in one)")
    async def join(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ Admin required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        target = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        if not target:
            return await interaction.edit_original_response(content="❌ Join a VC or pass channel.")

        try:
            print("JOIN: attempting connect to", target.id, target.name)
            vc = interaction.guild.voice_client

            if vc:
                print("JOIN: moving from", vc.channel, "to", target.name)
                await asyncio.wait_for(vc.move_to(target), timeout=10)
            else:
                print("JOIN: connecting fresh to", target.name)
                await asyncio.wait_for(target.connect(self_deaf=True), timeout=10)

            print("JOIN: connected OK")
            return await interaction.edit_original_response(content=f"✅ Joined **{target.name}**")

        except asyncio.TimeoutError:
            print("JOIN: TIMEOUT (voice networking issue)")
            return await interaction.edit_original_response(
                content="❌ Voice connect TIMEOUT. Railway par Discord voice usually work nahi karta."
            )
        except Exception:
            print("JOIN: ERROR")
            traceback.print_exc()
            return await interaction.edit_original_response(content="❌ Voice join failed. Check logs.")

    @app_commands.command(name="leave", description="Disconnect the bot from voice")
    async def leave(self, interaction: discord.Interaction):
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
