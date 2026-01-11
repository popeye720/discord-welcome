import discord
from discord.ext import commands
import asyncio
import time
from collections import defaultdict
from datetime import timedelta
from database.models import antispam_col  # ✅ SAME STRUCTURE

# ================= DEFAULT SETTINGS =================
DEFAULT_MESSAGE_LIMIT = 5
DEFAULT_TIME_WINDOW = 7
DEFAULT_TIMEOUT_MINUTES = 5  # 5 minutes

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.locked_users = set()

    # -------------------------------
    # PERMISSION CHECK
    # -------------------------------
    def is_admin_or_owner(self, member: discord.Member):
        return (
            member.id == member.guild.owner_id
            or member.guild_permissions.administrator
        )

    # -------------------------------
    # ENABLE ANTISPAM
    # -------------------------------
    @discord.app_commands.command(
        name="antispam",
        description="Enable anti-spam in your server with optional settings"
    )
    @discord.app_commands.describe(
        message_limit="Maximum messages allowed before timeout (default 5)",
        time_window="Time window in seconds to check messages (default 7)",
        timeout_minutes="Timeout duration in minutes (default 5)"
    )
    async def antispam(
        self,
        interaction: discord.Interaction,
        message_limit: int = DEFAULT_MESSAGE_LIMIT,
        time_window: int = DEFAULT_TIME_WINDOW,
        timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES
    ):
        if not self.is_admin_or_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Only **Admin or Owner** can use this command.", ephemeral=True
            )

        data = antispam_col.find_one({"guild_id": interaction.guild.id})
        if data:
            return await interaction.response.send_message(
                "⚠️ **Anti-Spam is already ENABLED.**", ephemeral=True
            )

        antispam_col.insert_one({
            "guild_id": interaction.guild.id,
            "enabled": True,
            "message_limit": message_limit,
            "time_window": time_window,
            "timeout_minutes": timeout_minutes
        })

        await interaction.response.send_message(
            "✅ **Anti-Spam Enabled**\n\n"
            f"📨 Messages: `{message_limit}` in `{time_window}` sec\n"
            f"⛔ Timeout: `{timeout_minutes}` minutes"
        )

    # -------------------------------
    # DISABLE ANTISPAM
    # -------------------------------
    @discord.app_commands.command(
        name="offantispam",
        description="Disable anti-spam in your server"
    )
    async def offantispam(self, interaction: discord.Interaction):
        if not self.is_admin_or_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Only **Admin or Owner** can use this command.", ephemeral=True
            )

        data = antispam_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return await interaction.response.send_message(
                "⚠️ **Anti-Spam is already DISABLED.**", ephemeral=True
            )

        antispam_col.delete_one({"guild_id": interaction.guild.id})
        await interaction.response.send_message("🟢 **Anti-Spam Disabled Successfully.**")

    # -------------------------------
    # STATUS ANTISPAM
    # -------------------------------
    @discord.app_commands.command(
        name="statusantispam",
        description="Check the status of anti-spam"
    )
    async def statusantispam(self, interaction: discord.Interaction):
        data = antispam_col.find_one({"guild_id": interaction.guild.id})

        if not data:
            return await interaction.response.send_message("🔴 **Anti-Spam Status:** OFF")

        embed = discord.Embed(
            title="🛡 Anti-Spam Status",
            color=discord.Color.green()
        )

        embed.add_field(name="Status", value="🟢 ENABLED", inline=False)
        embed.add_field(
            name="Rules",
            value=(
                f"📨 `{data['message_limit']}` messages in `{data['time_window']}` seconds\n"
                f"⛔ Timeout: `{data['timeout_minutes']}` minutes"
            ),
            inline=False
        )

        embed.add_field(
            name="Bypass",
            value="👑 Server Owner & Admins",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------
    # MESSAGE LISTENER
    # -------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = antispam_col.find_one(
            {"guild_id": message.guild.id, "enabled": True}
        )

        if not config:
            return

        member: discord.Member = message.author
        user_id = member.id

        # 👑 OWNER / ADMIN BYPASS
        if (
            user_id == message.guild.owner_id
            or member.guild_permissions.administrator
        ):
            return

        # ⛔ LOCKED USER
        if user_id in self.locked_users:
            try:
                await message.delete()
            except:
                pass
            return

        now = time.time()
        self.user_messages[user_id].append((now, message))

        # Cleanup old
        self.user_messages[user_id] = [
            (t, m) for t, m in self.user_messages[user_id]
            if now - t <= config["time_window"]
        ]

        # 🚨 SPAM DETECTED
        if len(self.user_messages[user_id]) >= config["message_limit"]:
            self.locked_users.add(user_id)

            # Delete spam messages
            for _, msg in self.user_messages[user_id]:
                try:
                    await msg.delete()
                except:
                    pass

            self.user_messages[user_id].clear()

            # 🔊 VC KICK
            try:
                if member.voice:
                    await member.move_to(None)
            except:
                pass

            # ⛔ TIMEOUT
            try:
                await member.timeout(
                    discord.utils.utcnow()
                    + timedelta(minutes=config["timeout_minutes"]),
                    reason="Spamming messages"
                )
            except:
                pass

            # 📩 DM
            try:
                await member.send(
                    embed=discord.Embed(
                        title="🚫 Spamming Detected",
                        description=(
                            "**You are sending messages too fast.**\n\n"
                            f"⏳ Timeout: `{config['timeout_minutes']}` minutes"
                        ),
                        color=discord.Color.red()
                    )
                )
            except:
                pass

            # 🔓 UNLOCK AFTER TIMEOUT
            await asyncio.sleep(config["timeout_minutes"] * 60)
            self.locked_users.discard(user_id)


async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
