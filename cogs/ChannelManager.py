import discord
from discord.ext import commands
from discord import app_commands

from utils.embed_color import create_embed


# ================= CHANNEL CLEAR =================

class ChannelManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="clear-all-msg",
        description="Clear all messages from the current channel"
    )
    @app_commands.guild_only()
    async def clear_all_msg(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        # ---------- USER PERMISSION ----------
        if not (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        ):
            embed = create_embed(
                title="❌ Permission Denied",
                description="Only **Admin** or **Server Owner** can use this command."
            )
            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        # ---------- BOT PERMISSION ----------
        if not guild.me.guild_permissions.manage_messages:
            embed = create_embed(
                title="❌ Missing Permission",
                description="I need **Manage Messages** permission."
            )
            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        # ---------- CLEAR MESSAGES ----------
        try:
            deleted = await channel.purge(limit=None)
            embed = create_embed(
                title="✅ Messages Cleared",
                description=f"Deleted **{len(deleted)}** messages in {channel.mention}"
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except discord.Forbidden:
            embed = create_embed(
                title="❌ Error",
                description="I don't have permission to clear messages here."
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except discord.HTTPException:
            embed = create_embed(
                title="❌ API Error",
                description="Something went wrong while clearing messages."
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )


# ================= SETUP =================

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelManager(bot))