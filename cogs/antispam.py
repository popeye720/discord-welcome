import discord
from discord.ext import commands
import asyncio
import time
from collections import defaultdict
from datetime import timedelta

# ================= SETTINGS =================
MESSAGE_LIMIT = 5
TIME_WINDOW = 7
TIMEOUT_SECONDS = 300  # 5 minutes

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.locked_users = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        member: discord.Member = message.author
        user_id = member.id
        now = time.time()

        # Store message timestamps
        self.user_messages[user_id].append((now, message))

        # Cleanup old messages
        self.user_messages[user_id] = [
            (t, m) for t, m in self.user_messages[user_id]
            if now - t <= TIME_WINDOW
        ]

        # 🚨 Spam detected
        if len(self.user_messages[user_id]) >= MESSAGE_LIMIT:
            if user_id in self.locked_users:
                return

            self.locked_users.add(user_id)

            # 🧹 Delete spam messages
            for _, msg in self.user_messages[user_id]:
                try:
                    await msg.delete()
                except:
                    pass

            self.user_messages[user_id].clear()

            # 🔊 VC se kick karo agar joined hai
            try:
                if member.voice:
                    await member.move_to(None)
            except:
                pass

            # ⛔ TIMEOUT
            try:
                await member.timeout(
                    discord.utils.utcnow() + timedelta(seconds=TIMEOUT_SECONDS),
                    reason="Spamming messages"
                )
            except Exception as e:
                print("❌ Timeout failed:", e)

            # 📩 DM warning (NO IMAGE)
            try:
                embed = discord.Embed(
                    title="🚫 Spamming Detected",
                    description=(
                        f"Hello {member.mention},\n\n"
                        "**Spamming is not allowed in this server.**\n\n"
                        "⏳ **Timeout:** 5 minutes\n"
                        "🔇 You cannot chat or join VC during this time."
                    ),
                    color=discord.Color.red()
                )

                await member.send(embed=embed)
            except:
                pass

            # 🔓 Unlock after timeout
            await asyncio.sleep(TIMEOUT_SECONDS)
            self.locked_users.discard(user_id)

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
