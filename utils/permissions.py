# utils/permissions.py
import discord

def is_admin_or_guild_owner(interaction: discord.Interaction) -> bool:
    """
    True if user is Guild Owner OR has Administrator permission.
    Works for slash commands + button interactions.
    """
    guild = interaction.guild
    if guild is None:
        return False

    user = interaction.user
    if user.id == guild.owner_id:
        return True

    perms = getattr(user, "guild_permissions", None)
    return bool(perms and perms.administrator)
