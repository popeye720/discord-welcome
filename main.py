import os
import discord
from discord.ext import commands
import asyncio

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True


# ================= CUSTOM BOT =================
class MyBot(commands.Bot):
    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"✅ Global slash commands synced: {len(synced)}")


# ================= BOT INIT =================
bot = MyBot(command_prefix="!", intents=intents)


# ================= TOKEN =================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")


# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    print(f"🌐 Connected to {len(bot.guilds)} guilds")

    from cogs.ticket import TicketButton, CloseTicketView
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())

    from cogs.guild_manager import GuildActionView
    bot.add_view(GuildActionView(bot, guild_id=0))

    try:
        from cogs.modal import ModalPanelView
        from database.models import modal_col

        count = 0
        for modal in modal_col.find({}):
            modal_id = modal.get("modal_id")
            message_id = modal.get("message_id")

            if modal_id and message_id:
                try:
                    bot.add_view(
                        ModalPanelView(modal_id),
                        message_id=int(message_id)
                    )
                    count += 1
                except Exception as e:
                    print("Modal view bind failed:", e)

        print(f"✅ Modal persistent views registered: {count}")

    except Exception as e:
        print("❌ Modal persistent register error:", e)

    try:
        from cogs.solarinfo import SolarInfoPanelView
        from database.models import solarinfo_col

        count = 0
        for panel in solarinfo_col.find({}):
            message_id = panel.get("message_id")

            if message_id:
                try:
                    bot.add_view(
                        SolarInfoPanelView(),
                        message_id=int(message_id)
                    )
                    count += 1
                except Exception as e:
                    print("Solar panel view bind failed:", e)

        print(f"✅ Solar persistent views registered: {count}")

    except Exception as e:
        print("❌ Solar persistent register error:", e)


@bot.event
async def on_guild_join(guild):
    print(f"🆕 Bot joined server: {guild.name} ({guild.id})")


# ================= LOAD COGS =================
async def main():
    async with bot:
        await bot.load_extension("cogs.autorole")
        await bot.load_extension("cogs.ticket")
        await bot.load_extension("cogs.auto_triggers")
        await bot.load_extension("cogs.ChannelManager")
        await bot.load_extension("cogs.Embedder")
        await bot.load_extension("cogs.antilinks")
        await bot.load_extension("cogs.dm")
        await bot.load_extension("cogs.greetings")
        await bot.load_extension("cogs.antispam")
        await bot.load_extension("cogs.guild_manager")
        await bot.load_extension("cogs.ytnotify")
        await bot.load_extension("cogs.scheduled_embeds")
        await bot.load_extension("cogs.modal")
        await bot.load_extension("cogs.dm_forward")
        await bot.load_extension("cogs.solarinfo")
        await bot.load_extension("cogs.autoping")
        await bot.start(TOKEN)


# ================= START BOT =================
asyncio.run(main())