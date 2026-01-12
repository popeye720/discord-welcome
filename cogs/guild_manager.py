import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from database.models import guilds_col, blacklisted_guilds_col  # <-- new collection
from datetime import datetime
import os

OWNER_ID = int(os.getenv("OWNER_ID"))

# ===============================
# 🔘 DM BUTTON VIEW (PERSISTENT)
# ===============================
class GuildActionView(View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "❌ You are not allowed to use this.",
                ephemeral=True
            )
            return False
        return True

    # 🚫 BLACKLIST BUTTON
    @discord.ui.button(
        label="Blacklist Server",
        style=discord.ButtonStyle.danger,
        custom_id="guild_blacklist_button"
    )
    async def blacklist_button(self, interaction: discord.Interaction, button: Button):
        guild_id_int = self.guild_id
        # Update main guild DB
        guilds_col.update_one({"guild_id": guild_id_int}, {"$set": {"blacklisted": True}}, upsert=True)
        # Save to permanent blacklist collection
        blacklisted_guilds_col.update_one(
            {"guild_id": guild_id_int},
            {"$set": {"blacklisted_at": datetime.utcnow()}},
            upsert=True
        )
        guild = self.bot.get_guild(guild_id_int)
        if guild:
            await guild.leave()
        await interaction.response.send_message(
            f"🚫 Server `{guild_id_int}` blacklisted & bot left.", ephemeral=True
        )

    # 🚪 LEAVE BUTTON
    @discord.ui.button(
        label="Leave Server",
        style=discord.ButtonStyle.secondary,
        custom_id="guild_leave_button"
    )
    async def leave_button(self, interaction: discord.Interaction, button: Button):
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return await interaction.response.send_message(
                "❌ Bot is not in this server.", ephemeral=True
            )
        await guild.leave()
        guilds_col.delete_one({"guild_id": self.guild_id})
        await interaction.response.send_message(
            f"✅ Bot left `{guild.name}` server.", ephemeral=True
        )

# ===============================
# 🤖 GUILD MANAGER COG (SLASH)
# ===============================
class GuildManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------------- AUTO LEAVE BLACKLISTED -----------------
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Check permanent blacklist first
        data = blacklisted_guilds_col.find_one({"guild_id": guild.id})
        if data:
            print(f"🚫 Blacklisted server tried adding bot: {guild.name}, leaving...")
            await guild.leave()
            return

        # Save to guilds_col normally
        data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "owner_id": guild.owner_id,
            "member_count": guild.member_count,
            "joined_at": datetime.utcnow(),
            "active": True,
            "blacklisted": False
        }
        guilds_col.update_one({"guild_id": guild.id}, {"$set": data}, upsert=True)

        owner = self.bot.get_user(OWNER_ID)
        if owner:
            embed = discord.Embed(
                title="🆕 Bot Added to Server",
                color=discord.Color.green()
            )
            embed.add_field(name="Server Name", value=guild.name, inline=False)
            embed.add_field(name="Server ID", value=str(guild.id), inline=False)
            embed.add_field(name="Members", value=guild.member_count, inline=False)

            view = GuildActionView(self.bot, guild.id)
            await owner.send(embed=embed, view=view)

        print(f"✅ Joined & saved: {guild.name} ({guild.id})")

    # ----------------- REMOVE -----------------
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        guilds_col.delete_one({"guild_id": guild.id})
        print(f"❌ Removed guild: {guild.name}")

    # ----------------- ON READY -----------------
    @commands.Cog.listener()
    async def on_ready(self):
        print("🔍 Checking blacklisted servers...")
        for guild in self.bot.guilds:
            data = blacklisted_guilds_col.find_one({"guild_id": guild.id})
            if data:
                print(f"🚫 Auto leaving blacklisted server: {guild.name}")
                await guild.leave()

    # ----------------- OWNER CHECK -----------------
    async def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == OWNER_ID and interaction.guild is None

    # ----------------- SLASH COMMANDS -----------------
    @app_commands.command(name="guilds", description="List all guilds the bot is in")
    async def guilds(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            return
        guilds = list(guilds_col.find())
        if not guilds:
            return await interaction.response.send_message("❌ No guilds found.", ephemeral=True)
        msg = "**🤖 Bot Servers:**\n\n"
        for g in guilds:
            status = "🚫 Blacklisted" if g.get("blacklisted") else "✅ Active"
            msg += f"• **{g['guild_name']}** (`{g['guild_id']}`) → {status}\n"
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="blacklist", description="Blacklist a server and leave it")
    async def blacklist(self, interaction: discord.Interaction, guild_id: str):
        if not await self.is_owner(interaction):
            return
        guild_id_int = int(guild_id)
        # Update both collections
        guilds_col.update_one({"guild_id": guild_id_int}, {"$set": {"blacklisted": True}}, upsert=True)
        blacklisted_guilds_col.update_one(
            {"guild_id": guild_id_int},
            {"$set": {"blacklisted_at": datetime.utcnow()}},
            upsert=True
        )
        guild = self.bot.get_guild(guild_id_int)
        if guild:
            await guild.leave()
        await interaction.response.send_message(
            f"🚫 Server `{guild_id_int}` blacklisted & bot left.", ephemeral=True
        )

    @app_commands.command(name="unblacklist", description="Remove server from blacklist")
    async def unblacklist(self, interaction: discord.Interaction, guild_id: str):
        if not await self.is_owner(interaction):
            return
        guild_id_int = int(guild_id)
        guilds_col.update_one({"guild_id": guild_id_int}, {"$set": {"blacklisted": False}}, upsert=True)
        blacklisted_guilds_col.delete_one({"guild_id": guild_id_int})
        await interaction.response.send_message(f"✅ Server `{guild_id_int}` unblacklisted.", ephemeral=True)

    @app_commands.command(name="leave", description="Bot leaves a specific guild")
    async def leave(self, interaction: discord.Interaction, guild_id: str):
        if not await self.is_owner(interaction):
            return
        guild_id_int = int(guild_id)
        guild = self.bot.get_guild(guild_id_int)
        if not guild:
            return await interaction.response.send_message("❌ Bot is not in this server.", ephemeral=True)
        await guild.leave()
        guilds_col.delete_one({"guild_id": guild_id_int})
        await interaction.response.send_message(f"✅ Bot left `{guild.name}` server.", ephemeral=True)

    @app_commands.command(name="blacklisted", description="List all permanently blacklisted servers")
    async def blacklisted(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            return
        blacklisted = list(blacklisted_guilds_col.find())
        if not blacklisted:
            return await interaction.response.send_message("❌ No blacklisted servers.", ephemeral=True)
        msg = "**🚫 Blacklisted Servers:**\n"
        for g in blacklisted:
            msg += f"• `{g['guild_id']}`\n"
        await interaction.response.send_message(msg, ephemeral=True)

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_owner(interaction)

# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(GuildManager(bot))
