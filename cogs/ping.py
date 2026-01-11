import discord
from discord.ext import commands
from discord import app_commands
import time


class Ping(commands.Cog):
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

    # ----------------- PING SLASH COMMAND -----------------
    @app_commands.command(name="ping", description="Check bot latency and status")
    async def ping(self, interaction: discord.Interaction):

        if not await self.is_admin_or_owner(interaction):
            return

        # Websocket latency
        ws_latency = round(self.bot.latency * 1000)

        # Initial response (acts like ctx.send)
        start = time.perf_counter()
        await interaction.response.send_message("🏓 Checking ping...", ephemeral=False)
        end = time.perf_counter()

        msg_latency = round((end - start) * 1000)

        embed = discord.Embed(
            title="🏓 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 Bot Status",
            value="Online",
            inline=False
        )

        embed.add_field(
            name="📶 WebSocket Latency",
            value=f"`{ws_latency} ms`",
            inline=True
        )

        embed.add_field(
            name="⏱ Message Latency",
            value=f"`{msg_latency} ms`",
            inline=True
        )

        embed.set_footer(text="Bot is running smoothly 🚀")

        # Edit original response (same as msg.edit)
        await interaction.edit_original_response(
            content=None,
            embed=embed
        )

    # ----------------- GLOBAL CHECK (OPTIONAL BUT SAME STYLE) -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
