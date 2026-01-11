import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime


class Profile(commands.Cog):
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

    # ----------------- PROFILE SLASH COMMAND -----------------
    @app_commands.command(
        name="profile",
        description="Show profile of a user (mention or user ID)"
    )
    @app_commands.describe(user="Mention a user or provide user ID")
    async def profile(
        self,
        interaction: discord.Interaction,
        user: str
    ):
        if not await self.is_admin_or_owner(interaction):
            return

        await interaction.response.defer(ephemeral=False)

        # 🔥 Resolve mention OR ID (same logic)
        member = None

        if user.isdigit():
            member = interaction.guild.get_member(int(user))
        else:
            if interaction.data.get("resolved", {}).get("users"):
                user_id = next(iter(interaction.data["resolved"]["users"]))
                member = interaction.guild.get_member(int(user_id))

        if not member:
            return await interaction.edit_original_response(
                content="❌ User not found in this server."
            )

        roles = [r for r in member.roles if r.name != "@everyone"]
        top_role = roles[-1].mention if roles else "None"

        embed = discord.Embed(
            title="👤 User Profile",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%d %b %Y"),
            inline=True
        )
        embed.add_field(
            name="Joined Server",
            value=member.joined_at.strftime("%d %b %Y"),
            inline=True
        )
        embed.add_field(name="Roles Count", value=len(roles), inline=True)
        embed.add_field(name="Top Role", value=top_role, inline=True)

        embed.set_footer(text="TEJAS • One bot. Infinite possibilities.")

        await interaction.edit_original_response(
            content=None,
            embed=embed
        )

    # ----------------- GLOBAL CHECK (SAME STYLE AS PING) -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
