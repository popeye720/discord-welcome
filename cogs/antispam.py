import discord
from discord.ext import commands
import os
import asyncio
import time
from collections import defaultdict

# ================= ENV =================
EMBED_IMAGE_URL = os.getenv("EMBED_IMAGE_URL")

# ================= SETTINGS =================
MESSAGE_LIMIT = 5        # kitne messages
TIME_WINDOW = 7          # seconds ke andar
TIMEOUT_SECONDS = 300    # 5 minutes

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.locked_users = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        now = time.time()

        # Store timestamps
        self.user_messages[user_id].append((now, message))

        # Remove old messages
        self.user_messages[user_id] = [
            (t, m) for t, m in self.user_messages[user_id]
            if now - t <= TIME_WINDOW
        ]

        # Spam detected
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

            # ⛔ Timeout user
            try:
                await message.author.timeout(
                    discord.utils.utcnow() + discord.timedelta(seconds=TIMEOUT_SECONDS),
                    reason="Spamming messages"
                )
            except:
                pass

            # 📩 DM Warning Embed
            try:
                embed = discord.Embed(
                    title="🚫 Spamming Detected",
                    description=(
                        f"Hello {message.author.mention},\n\n"
                        "**Spamming is not allowed in this server.**\n"
                        "You were sending messages too fast.\n\n"
                        "⏳ **Timeout Duration:** 5 minutes\n\n"
                        "Please follow the rules and chat responsibly."
                    ),
                    color=discord.Color.red()
                )

                if EMBED_IMAGE_URL:
                    embed.set_image(url=EMBED_IMAGE_URL)

                await message.author.send(embed=embed)
            except:
                pass

            # 🔓 Unlock after timeout
            await asyncio.sleep(TIMEOUT_SECONDS)
            self.locked_users.discard(user_id)

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
