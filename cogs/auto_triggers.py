import discord
from discord.ext import commands
from discord import app_commands
import time

from database.models import autotrigger_col

DEFAULT_COOLDOWN = 10  # default 10 seconds


class AutoTriggers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}  # user_id : last_used_time

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
    # ADD TRIGGER
    # -------------------------------
    @app_commands.command(
        name="addtrigger",
        description="Add an auto-reply trigger (optional cooldown in seconds)"
    )
    @app_commands.describe(
        trigger="The trigger word/phrase",
        reply="The reply for the trigger",
        cooldown="Optional cooldown in seconds (default 10s)"
    )
    async def addtrigger(
        self,
        interaction: discord.Interaction,
        trigger: str,
        reply: str,
        cooldown: int = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        trigger = trigger.lower()
        cooldown = cooldown if cooldown is not None else DEFAULT_COOLDOWN

        # Get guild document or create if not exists
        guild_data = autotrigger_col.find_one({"guild_id": interaction.guild.id})
        if not guild_data:
            guild_data = {"guild_id": interaction.guild.id, "triggers": {}}
            autotrigger_col.insert_one(guild_data)

        # Check if trigger exists
        if trigger in guild_data["triggers"]:
            return await interaction.response.send_message(
                f"⚠️ Trigger `{trigger}` already exists.",
                ephemeral=True
            )

        # Add trigger
        autotrigger_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"triggers.{trigger}": {"reply": reply, "cooldown": cooldown}}}
        )

        await interaction.response.send_message(
            f"✅ Trigger `{trigger}` added with cooldown `{cooldown}s`.",
            ephemeral=True
        )

    # -------------------------------
    # DELETE TRIGGER
    # -------------------------------
    @app_commands.command(name="deltrigger", description="Delete an auto-reply trigger")
    @app_commands.describe(trigger="The trigger word/phrase to delete")
    async def deltrigger(
        self,
        interaction: discord.Interaction,
        trigger: str
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        trigger = trigger.lower()

        guild_data = autotrigger_col.find_one({"guild_id": interaction.guild.id})
        if not guild_data or trigger not in guild_data.get("triggers", {}):
            return await interaction.response.send_message(
                f"⚠️ Trigger `{trigger}` does not exist.",
                ephemeral=True
            )

        autotrigger_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$unset": {f"triggers.{trigger}": ""}}
        )

        await interaction.response.send_message(
            f"✅ Trigger `{trigger}` deleted successfully.",
            ephemeral=True
        )

    # -------------------------------
    # LIST TRIGGERS
    # -------------------------------
    @app_commands.command(name="triggerlist", description="List all triggers")
    async def triggerlist(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        guild_data = autotrigger_col.find_one({"guild_id": interaction.guild.id})
        triggers = guild_data.get("triggers", {}) if guild_data else {}

        if not triggers:
            return await interaction.response.send_message(
                "No triggers are set yet.",
                ephemeral=True
            )

        text = "\n".join([f"**{t}** → {v.get('cooldown', DEFAULT_COOLDOWN)}s" for t, v in triggers.items()])

        embed = discord.Embed(
            title="Trigger List",
            description=text,
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------------
    # MESSAGE LISTENER (AUTO REPLY)
    # -------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.lower().strip()

        guild_data = autotrigger_col.find_one({"guild_id": message.guild.id})
        triggers = guild_data.get("triggers", {}) if guild_data else {}

        if content not in triggers:
            return

        data = triggers[content]

        # cooldown per user
        now = time.time()
        last = self.cooldowns.get(message.author.id, 0)
        cooldown = data.get("cooldown", DEFAULT_COOLDOWN)
        if now - last < cooldown:
            return

        self.cooldowns[message.author.id] = now
        await message.reply(
            data["reply"],
            mention_author=False
        )


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoTriggers(bot))