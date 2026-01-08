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
DEFAULT_TIMEOUT_SECONDS = 600  # 10 minutes

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
    @commands.command(name="antispam")
    @commands.guild_only()
    async def antispam(self, ctx):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Owner** can use this command.")

        data = antispam_col.find_one({"guild_id": ctx.guild.id})

        if data:
            return await ctx.reply("⚠️ **Anti-Spam is already ENABLED.**")

        antispam_col.insert_one({
            "guild_id": ctx.guild.id,
            "enabled": True,
            "message_limit": DEFAULT_MESSAGE_LIMIT,
            "time_window": DEFAULT_TIME_WINDOW,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS
        })

        await ctx.reply(
            "✅ **Anti-Spam Enabled**\n\n"
            f"📨 Messages: `{DEFAULT_MESSAGE_LIMIT}` in `{DEFAULT_TIME_WINDOW}` sec\n"
            f"⛔ Timeout: `{DEFAULT_TIMEOUT_SECONDS // 60}` minutes"
        )

    # -------------------------------
    # DISABLE ANTISPAM
    # -------------------------------
    @commands.command(name="offantispam")
    @commands.guild_only()
    async def offantispam(self, ctx):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Owner** can use this command.")

        data = antispam_col.find_one({"guild_id": ctx.guild.id})
        if not data:
            return await ctx.reply("⚠️ **Anti-Spam is already DISABLED.**")

        antispam_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.reply("🟢 **Anti-Spam Disabled Successfully.**")

    # -------------------------------
    # STATUS ANTISPAM
    # -------------------------------
    @commands.command(name="statusantispam")
    @commands.guild_only()
    async def statusantispam(self, ctx):
        data = antispam_col.find_one({"guild_id": ctx.guild.id})

        if not data:
            return await ctx.reply("🔴 **Anti-Spam Status:** OFF")

        embed = discord.Embed(
            title="🛡 Anti-Spam Status",
            color=discord.Color.green()
        )

        embed.add_field(name="Status", value="🟢 ENABLED", inline=False)
        embed.add_field(
            name="Rules",
            value=(
                f"📨 `{data['message_limit']}` messages in `{data['time_window']}` seconds\n"
                f"⛔ Timeout: `{data['timeout_seconds'] // 60}` minutes"
            ),
            inline=False
        )

        embed.add_field(
            name="Bypass",
            value="👑 Server Owner & Admins",
            inline=False
        )

        await ctx.reply(embed=embed)

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
                    + timedelta(seconds=config["timeout_seconds"]),
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
                            f"⏳ Timeout: `{config['timeout_seconds'] // 60}` minutes"
                        ),
                        color=discord.Color.red()
                    )
                )
            except:
                pass

            # 🔓 UNLOCK AFTER TIMEOUT
            await asyncio.sleep(config["timeout_seconds"])
            self.locked_users.discard(user_id)

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
