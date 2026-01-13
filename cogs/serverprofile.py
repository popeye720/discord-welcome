import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime


class ServerProfile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK (ADMIN / OWNER) -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ----------------- /serverprofile -----------------
    @app_commands.command(name="server-profile", description="Show server profile (Admin/Owner only)")
    async def serverprofile(self, interaction: discord.Interaction):
        # permission
        if not await self.is_admin_or_owner(interaction):
            return  # ref code jaisa: silently ignore so normal users ko kuch leak na ho

        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
    
        # counts
        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        embed = discord.Embed(
            title="🏠 Server Profile",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)

        embed.add_field(
            name="Owner",
            value=guild.owner.mention if guild.owner else "Unknown",
            inline=True
        )

        embed.add_field(
            name="Created On",
            value=guild.created_at.strftime("%d %b %Y"),
            inline=True
        )

        embed.add_field(
            name="Members",
            value=f"👤 {humans} | 🤖 {bots}",
            inline=True
        )

        boosts = guild.premium_subscription_count or 0
        embed.add_field(
            name="Boosts",
            value=f"Level {guild.premium_tier} ({boosts})",
            inline=True
        )

        embed.add_field(
            name="Channels",
            value=f"💬 {text_channels} | 🔊 {voice_channels} | 📁 {categories}",
            inline=True
        )

        embed.add_field(
            name="Roles",
            value=str(len(guild.roles)),
            inline=True
        )

        embed.set_footer(text="TEJAS • One bot. Infinite possibilities.")

        # slash reply (ephemeral so only admin/owner sees)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- GLOBAL CHECK (optional, ref code jaisa) -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(ServerProfile(bot))
