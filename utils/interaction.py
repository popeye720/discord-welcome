# utils/interaction.py
import discord

async def safe_ephemeral(interaction: discord.Interaction, content: str):
    """
    Safely send an ephemeral message (handles already-responded interactions).
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)
    except Exception:
        pass
