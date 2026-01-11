import discord
from discord.ext import commands
from discord import app_commands
import time


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- ADMIN / OWNER CHECK --------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if guild is None:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # -------- PING COMMAND --------
    @app_commands.command(name="ping", description="Check bot latency")
    @app_commands.default_permissions(administrator=True)
    async def ping(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only server owner or admins can use this.",
                ephemeral=True
            )

        # Websocket latency
        ws_latency = round(self.bot.latency * 1000)

        # Message latency
        start = time.perf_counter()
        await interaction.response.send_message("🏓 Checking ping...")
        msg = await interaction.original_response()
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

        await msg.edit(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(Ping(bot))
