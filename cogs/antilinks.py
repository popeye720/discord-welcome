import re
import discord
from discord.ext import commands
from discord import app_commands
from database.models import antilinks_col  # 👈 Mongo collection

LINK_REGEX = re.compile(
    r"(https?:\/\/|www\.)\S+",
    re.IGNORECASE
)

class AntiLinks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------
    # PERMISSION CHECK
    # -------------------------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # -------------------------------
    # ENABLE / ADD ROLE
    # -------------------------------
    @app_commands.command(name="antilinks", description="Enable Anti-Links")
    @app_commands.describe(role="Role that can send links")
    async def antilinks(
        self,
        interaction: discord.Interaction,
        role: discord.Role = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        data = antilinks_col.find_one({"guild_id": interaction.guild.id})

        # 🟢 FIRST TIME ENABLE
        if not data:
            antilinks_col.insert_one({
                "guild_id": interaction.guild.id,
                "enabled": True,
                "allowed_roles": [role.id] if role else []
            })

            if role:
                return await interaction.response.send_message(
                    f"✅ **Anti-Links Enabled**\n"
                    f"🔓 Allowed Role: {role.mention}",
                    ephemeral=True
                )
            return await interaction.response.send_message(
                "✅ **Anti-Links Enabled**\n"
                "🔒 Only **Admins & Owner** can send links",
                ephemeral=True
            )

        # 🔁 ALREADY ENABLED
        if data.get("enabled"):
            if not role:
                return await interaction.response.send_message(
                    "⚠️ **Anti-Links is already ENABLED**.",
                    ephemeral=True
                )

            allowed_roles = data.get("allowed_roles", [])

            if role.id in allowed_roles:
                return await interaction.response.send_message(
                    f"⚠️ {role.mention} is **already allowed**.",
                    ephemeral=True
                )

            antilinks_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$push": {"allowed_roles": role.id}}
            )

            return await interaction.response.send_message(
                f"✅ Role Added: {role.mention} can now send links.",
                ephemeral=True
            )

    # -------------------------------
    # DISABLE ANTILINKS
    # -------------------------------
    @app_commands.command(name="offantilinks", description="Disable Anti-Links")
    async def offantilinks(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        data = antilinks_col.find_one({"guild_id": interaction.guild.id})

        if not data:
            return await interaction.response.send_message(
                "⚠️ **Anti-Links is already DISABLED**.",
                ephemeral=True
            )

        antilinks_col.delete_one({"guild_id": interaction.guild.id})
        await interaction.response.send_message(
            "🟢 **Anti-Links Disabled Successfully**.",
            ephemeral=True
        )

    # -------------------------------
    # STATUS COMMAND
    # -------------------------------
    @app_commands.command(name="statusantilinks", description="Check Anti-Links status")
    async def statusantilinks(self, interaction: discord.Interaction):
        data = antilinks_col.find_one({"guild_id": interaction.guild.id})

        if not data:
            return await interaction.response.send_message(
                "🔴 **Anti-Links Status:** OFF",
                ephemeral=True
            )

        role_mentions = []
        for rid in data.get("allowed_roles", []):
            role = interaction.guild.get_role(rid)
            if role:
                role_mentions.append(role.mention)

        embed = discord.Embed(
            title="🔗 Anti-Links Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Status",
            value="🟢 ENABLED",
            inline=False
        )

        embed.add_field(
            name="Allowed Users",
            value="👑 Admins & Server Owner",
            inline=False
        )

        embed.add_field(
            name="Allowed Roles",
            value=", ".join(role_mentions) if role_mentions else "None",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------------
    # MESSAGE LISTENER
    # -------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        data = antilinks_col.find_one(
            {"guild_id": message.guild.id, "enabled": True},
            {"allowed_roles": 1}
        )

        if not data:
            return

        # -------------------------------
        # ALLOW !audiodown COMMAND
        # -------------------------------
        if message.content.startswith("!audiodown "):
            return

        # -------------------------------
        # CHECK FOR LINKS
        # -------------------------------
        if not LINK_REGEX.search(message.content):
            return

        # 👑 OWNER
        if message.author.id == message.guild.owner_id:
            return

        # 🛡 ADMIN
        if message.author.guild_permissions.administrator:
            return

        # 🎭 ROLE EXCEPTION
        allowed_roles = data.get("allowed_roles", [])
        if allowed_roles and any(r.id in allowed_roles for r in message.author.roles):
            return

        # ❌ DELETE if message is ONLY a link
        if message.content.strip() == LINK_REGEX.search(message.content).group(0):
            try:
                await message.delete()
            except discord.Forbidden:
                return

            # 📩 DM
            try:
                await message.author.send(
                    embed=discord.Embed(
                        title="🚫 Links Not Allowed",
                        description="You are not allowed to send links in this server.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass

    # -------------------------------
    # GLOBAL CHECK FOR SLASH COMMANDS
    # -------------------------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(AntiLinks(bot))
