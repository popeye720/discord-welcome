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

    async def _force_drop(self, guild: discord.Guild) -> bool:
        """
        Tries multiple ways to drop voice connection.
        Returns True if we *think* we dropped successfully.
        """
        vc = guild.voice_client
        if vc:
            try:
                if vc.is_playing():
                    vc.stop()
            except:
                pass

            # try normal disconnect
            try:
                await vc.disconnect(force=True)
                await asyncio.sleep(1)
            except:
                try:
                    await vc.disconnect()
                    await asyncio.sleep(1)
                except:
                    pass

        # Fallback: force voice state update (kills ghost connections sometimes)
        try:
            await guild.change_voice_state(channel=None)
            await asyncio.sleep(1)
        except:
            pass

        # Re-check
        vc2 = guild.voice_client
        return (vc2 is None) or (not vc2.is_connected())

    @app_commands.command(name="voicejoin", description="Make the bot join a voice channel (robust)")
    @app_commands.describe(channel="Voice channel (optional)")
    async def voicejoin(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None
    ):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ Admin required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        target = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        if not target:
            return await interaction.edit_original_response(content="❌ Join a VC or pass channel.")

        guild = interaction.guild
        vc = guild.voice_client

        try:
            # If already connected somewhere, move
            if vc and vc.is_connected():
                await asyncio.wait_for(vc.move_to(target), timeout=10)
                # verify
                ok = vc.is_connected() and vc.channel and vc.channel.id == target.id
                return await interaction.edit_original_response(
                    content=f"✅ Moved to **{target.name}**" if ok else f"⚠️ Move attempted, but state looks inconsistent."
                )

            # If stale client exists, force drop first
            if vc and not vc.is_connected():
                await self._force_drop(guild)

            # Connect fresh
            vc = await asyncio.wait_for(target.connect(self_deaf=True), timeout=10)

            # Verify actual connection
            ok = vc.is_connected() and vc.channel and vc.channel.id == target.id
            if ok:
                return await interaction.edit_original_response(content=f"✅ Joined **{target.name}**")
            else:
                # Not really connected; clean up so bot doesn't ghost
                await self._force_drop(guild)
                return await interaction.edit_original_response(
                    content="❌ Join failed (voice state inconsistent). Hosting/network issue."
                )

        except asyncio.TimeoutError:
            # Timeout => cleanup to avoid ghost bot
            await self._force_drop(guild)
            return await interaction.edit_original_response(
                content="❌ Voice connect TIMEOUT (hosting/network issue). Cleaned up connection."
            )
        except Exception:
            traceback.print_exc()
            await self._force_drop(guild)
            return await interaction.edit_original_response(
                content="❌ Voice join failed. Cleaned up. Check logs."
            )

    @app_commands.command(name="voiceleave", description="Disconnect the bot from voice (force)")
    async def voiceleave(self, interaction: discord.Interaction):
        if not self.has_permissions(interaction):
            return await interaction.response.send_message("❌ Admin required.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        vc = guild.voice_client

        if not vc:
            return await interaction.edit_original_response(content="❌ Not connected (no voice client).")

        dropped = await self._force_drop(guild)

        # Double-check state
        vc2 = guild.voice_client
        state = f"After leave: voice_client={vc2}, connected={(vc2.is_connected() if vc2 else None)}"
        print(state)

        return await interaction.edit_original_response(
            content="✅ Disconnected (force cleanup done)." if dropped else "⚠️ Leave attempted, but Discord still shows ghost. Wait 10–30s or rejoin server."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(JoinLeave(bot))
