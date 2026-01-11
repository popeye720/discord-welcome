import discord
from discord.ext import commands
from discord import app_commands
from database.models import greetings_col


class Greetings(commands.Cog):
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

    # ----------------- SET WELCOME -----------------
    @app_commands.command(name="setwelcome", description="Set the welcome channel")
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)

        # ❌ Already set check
        existing = greetings_col.find_one({"guild_id": interaction.guild.id})
        if existing:
            return await interaction.response.send_message(
                "⚠️ Welcome is already set. Use `/delwelcome` first.",
                ephemeral=True
            )

        greetings_col.insert_one({
            "guild_id": interaction.guild.id,
            "channel_id": channel.id
        })

        await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}", ephemeral=True)

    # ----------------- DELETE WELCOME -----------------
    @app_commands.command(name="delwelcome", description="Delete the welcome channel")
    async def delete_welcome(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)

        result = greetings_col.find_one_and_delete({"guild_id": interaction.guild.id})
        if not result:
            return await interaction.response.send_message("❌ Welcome is not set.", ephemeral=True)

        await interaction.response.send_message("✅ Welcome system deleted successfully.", ephemeral=True)

    # ----------------- TEST WELCOME -----------------
    @app_commands.command(name="testgreetings", description="Test welcome message")
    async def test_greetings(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)

        data = greetings_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return await interaction.response.send_message("❌ Welcome is not set.", ephemeral=True)

        channel = interaction.guild.get_channel(data["channel_id"])
        if not channel:
            return await interaction.response.send_message("❌ Saved channel not found.", ephemeral=True)

        await channel.send(f"{interaction.user.mention} welcome to the server")
        await interaction.response.send_message("✅ Test welcome sent.", ephemeral=True)

    # ----------------- AUTO WELCOME ON JOIN -----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = greetings_col.find_one({"guild_id": member.guild.id})
        if not data:
            return

        channel = member.guild.get_channel(data["channel_id"])
        if not channel:
            return

        await channel.send(f"{member.mention} welcome to the server")

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Greetings(bot))
