import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from database.models import autorenamer_col  # same DB, same collection


class AutoRename(commands.Cog):
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

    # ----------------- AUTO RENAME SETUP -----------------
    @app_commands.command(name="autorenam", description="Auto rename new members")
    async def autorenam(self, interaction: discord.Interaction, word: str):
        if not await self.is_admin_or_owner(interaction):
            return

        guild_id = interaction.guild.id

        # 🔒 DUPLICATE ENABLE CHECK
        existing = autorenamer_col.find_one(
            {"guild_id": guild_id, "enabled": True}
        )
        if existing:
            return await interaction.response.send_message(
                "❌ Auto rename is already **enabled** for this server.",
                ephemeral=True
            )

        autorenamer_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"prefix": word, "enabled": True}},
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Auto rename enabled → `{word} USERNAME`",
            ephemeral=True
        )

    # ----------------- STOP AUTO RENAME -----------------
    @app_commands.command(name="stopautorenam", description="Disable auto rename")
    async def stopautorenam(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        guild_id = interaction.guild.id

        # 🔒 DUPLICATE DISABLE CHECK
        existing = autorenamer_col.find_one(
            {"guild_id": guild_id, "enabled": True}
        )
        if not existing:
            return await interaction.response.send_message(
                "❌ Auto rename is already **disabled** for this server.",
                ephemeral=True
            )

        autorenamer_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"enabled": False}}
        )

        await interaction.response.send_message(
            "🛑 Auto rename disabled",
            ephemeral=True
        )

    # ----------------- MEMBER JOIN EVENT -----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        data = autorenamer_col.find_one(
            {"guild_id": member.guild.id, "enabled": True}
        )
        if not data:
            return

        try:
            new_name = f"{data['prefix']} {member.name}"
            await member.edit(nick=new_name)
        except:
            pass

    # ----------------- RENAME SINGLE MEMBER -----------------
    @app_commands.command(name="memberrenam", description="Rename a member")
    async def memberrenam(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        word: str
    ):
        if not await self.is_admin_or_owner(interaction):
            return

        if member.bot or member.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "❌ Cannot rename this user",
                ephemeral=True
            )

        await member.edit(nick=f"{word} {member.name}")
        await interaction.response.send_message(
            f"✅ Renamed **{member.name}**",
            ephemeral=True
        )

    # ----------------- RENAME ALL MEMBERS -----------------
    @app_commands.command(name="allmemberrenam", description="Rename all members")
    async def allmemberrenam(self, interaction: discord.Interaction, word: str):
        if not await self.is_admin_or_owner(interaction):
            return

        await interaction.response.send_message(
            "⏳ Renaming members...",
            ephemeral=True
        )

        guild = interaction.guild
        for member in guild.members:
            if member.bot or member.id == guild.owner_id:
                continue
            try:
                await member.edit(nick=f"{word} {member.name}")
                await asyncio.sleep(0.7)  # rate limit safe
            except:
                continue

        await interaction.followup.send(
            "✅ All members renamed",
            ephemeral=True
        )

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRename(bot))
