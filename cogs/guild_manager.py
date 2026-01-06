import discord
from discord.ext import commands
from discord.ui import View, Button
from database.models import guilds_col
from datetime import datetime
import os

OWNER_ID = int(os.getenv("OWNER_ID"))

# ===============================
# 🔘 DM BUTTON VIEW
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
    @discord.ui.button(label="Blacklist Server", style=discord.ButtonStyle.danger)
    async def blacklist_button(self, interaction: discord.Interaction, button: Button):

        guilds_col.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"blacklisted": True}},
            upsert=True
        )

        guild = self.bot.get_guild(self.guild_id)
        if guild:
            await guild.leave()

        await interaction.response.send_message(
            f"🚫 Server `{self.guild_id}` blacklisted & bot left.",
            ephemeral=True
        )

    # 🚪 LEAVE BUTTON
    @discord.ui.button(label="Leave Server", style=discord.ButtonStyle.secondary)
    async def leave_button(self, interaction: discord.Interaction, button: Button):

        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return await interaction.response.send_message(
                "❌ Bot is server me nahi hai.",
                ephemeral=True
            )

        await guild.leave()
        guilds_col.delete_one({"guild_id": self.guild_id})

        await interaction.response.send_message(
            f"✅ Bot left `{guild.name}` server.",
            ephemeral=True
        )

# ===============================
# 🤖 GUILD MANAGER COG
# ===============================
class GuildManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===============================
    # 🆕 Bot added to server
    # ===============================
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):

        data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "owner_id": guild.owner_id,
            "member_count": guild.member_count,
            "joined_at": datetime.utcnow(),
            "active": True,
            "blacklisted": False
        }

        guilds_col.update_one(
            {"guild_id": guild.id},
            {"$set": data},
            upsert=True
        )

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

    # ===============================
    # ❌ Bot removed
    # ===============================
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        guilds_col.delete_one({"guild_id": guild.id})
        print(f"❌ Removed guild: {guild.name}")

    # ===============================
    # 🔄 Restart blacklist check
    # ===============================
    @commands.Cog.listener()
    async def on_ready(self):
        print("🔍 Checking blacklisted servers...")

        for guild in self.bot.guilds:
            data = guilds_col.find_one({"guild_id": guild.id})
            if data and data.get("blacklisted", False):
                print(f"🚫 Auto leaving blacklisted server: {guild.name}")
                await guild.leave()
                guilds_col.delete_one({"guild_id": guild.id})

    # ===============================
    # 🔐 DM + OWNER CHECK
    # ===============================
    def _check_dm_owner(self, ctx):
        return ctx.guild is None and ctx.author.id == OWNER_ID

    # ===============================
    # 📜 List servers (DM)
    # ===============================
    @commands.command()
    async def guilds(self, ctx):
        if not self._check_dm_owner(ctx):
            return

        guilds = list(guilds_col.find())
        if not guilds:
            return await ctx.send("❌ No guilds found.")

        msg = "**🤖 Bot Servers:**\n\n"
        for g in guilds:
            status = "🚫 Blacklisted" if g.get("blacklisted") else "✅ Active"
            msg += f"• **{g['guild_name']}** (`{g['guild_id']}`) → {status}\n"

        await ctx.send(msg)

    # ===============================
    # 🚫 Blacklist (DM COMMAND)
    # ===============================
    @commands.command()
    async def blacklist(self, ctx, guild_id: int):
        if not self._check_dm_owner(ctx):
            return

        guilds_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"blacklisted": True}},
            upsert=True
        )

        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()

        await ctx.send(f"🚫 Server `{guild_id}` blacklisted & bot left.")

    # ===============================
    # ♻️ Unblacklist (DM COMMAND)
    # ===============================
    @commands.command()
    async def unblacklist(self, ctx, guild_id: int):
        if not self._check_dm_owner(ctx):
            return

        guilds_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"blacklisted": False}},
            upsert=True
        )

        await ctx.send(f"✅ Server `{guild_id}` unblacklisted.")

    # ===============================
    # 🚪 Leave server (DM COMMAND)
    # ===============================
    @commands.command()
    async def leave(self, ctx, guild_id: int):
        if not self._check_dm_owner(ctx):
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("❌ Bot is server me nahi hai.")

        await guild.leave()
        guilds_col.delete_one({"guild_id": guild_id})

        await ctx.send(f"✅ Bot left `{guild.name}` server.")

async def setup(bot):
    await bot.add_cog(GuildManager(bot))
