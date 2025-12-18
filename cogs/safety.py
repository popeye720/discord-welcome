import discord
from discord.ext import commands
import time
from datetime import timedelta

class Safety(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # (guild_id, channel_id, user_id) : list of (timestamp, message)
        self.user_messages = {}

        self.MESSAGE_LIMIT = 5
        self.TIME_WINDOW = 6
        self.TIMEOUT_SECONDS = 120

        self.LINK_KEYWORDS = [
            "http://",
            "https://",
            "discord.gg/",
            "discord.com/invite"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        key = (message.guild.id, message.channel.id, message.author.id)
        now = time.time()

        # ===== LINK DETECTION =====
        if any(link in message.content.lower() for link in self.LINK_KEYWORDS):
            try:
                await message.delete()
            except:
                pass

        # ===== STORE MESSAGE =====
        msgs = self.user_messages.get(key, [])
        msgs.append((now, message))

        # keep only recent window messages
        msgs = [(t, m) for t, m in msgs if now - t <= self.TIME_WINDOW]
        self.user_messages[key] = msgs

        # ===== SPAM TRIGGER =====
        if len(msgs) >= self.MESSAGE_LIMIT:
            try:
                # timeout user
                await message.author.timeout(
                    timedelta(seconds=self.TIMEOUT_SECONDS),
                    reason="Spam detected"
                )

                # delete spam messages in this channel
                for _, msg in msgs:
                    try:
                        await msg.delete()
                    except:
                        pass

                # ===== DM WARNING =====
                try:
                    embed = discord.Embed(
                        description=(
                            "⚠️ **Spam Detected**\n\n"
                            f"You were sending messages too fast in **{message.guild.name}**.\n\n"
                            f"⏳ **Timeout:** {self.TIMEOUT_SECONDS} seconds\n\n"
                            "Please slow down and follow the rules."
                        ),
                        color=discord.Color.red()
                    )
                    await message.author.send(embed=embed)
                except:
                    pass

            except:
                pass

            # reset only this channel-user combo
            self.user_messages.pop(key, None)
            return

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Safety(bot))
