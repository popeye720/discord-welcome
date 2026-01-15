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
        # 🔥 CORRECT PLACE FOR SLASH SYNC
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

    # 🔥 REGISTER PERSISTENT VIEWS (Ticket System)
    from cogs.ticket import TicketButton, CloseTicketView
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())

    # 🔥 REGISTER GUILD MANAGER PERSISTENT VIEW
    from cogs.guild_manager import GuildActionView
    bot.add_view(GuildActionView(bot, guild_id=0))

    # 🔥 REGISTER FORMS PERSISTENT VIEW
    from cogs.forms import UserFormView
    bot.add_view(UserFormView(guild_id=0))

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

@bot.event
async def on_guild_join(guild):
    print(f"🆕 Bot joined server: {guild.name} ({guild.id})")


# ================= LOAD COGS =================
async def main():
    async with bot:
        await bot.load_extension("cogs.autorole")
        await bot.load_extension("cogs.ticket")
        await bot.load_extension("cogs.join_to_create")
        await bot.load_extension("cogs.auto_triggers")
        await bot.load_extension("cogs.free_games")
        await bot.load_extension("cogs.ChannelManager")
        await bot.load_extension("cogs.Embedder")
        await bot.load_extension("cogs.reactionRole")
        await bot.load_extension("cogs.antilinks")
        await bot.load_extension("cogs.dm")
        await bot.load_extension("cogs.serverprofile")
        await bot.load_extension("cogs.greetings")
        await bot.load_extension("cogs.serverstats")
        await bot.load_extension("cogs.streammode")
        await bot.load_extension("cogs.clip")
        await bot.load_extension("cogs.antispam")
        await bot.load_extension("cogs.guild_manager")
        await bot.load_extension("cogs.ytnotify")
        await bot.load_extension("cogs.profile")
        await bot.load_extension("cogs.fungames")
        await bot.load_extension("cogs.ping")
        await bot.load_extension("cogs.forms")
        await bot.load_extension("cogs.audiodownloader")
        await bot.load_extension("cogs.scheduled_embeds")
        await bot.load_extension("cogs.search")
        await bot.load_extension("cogs.autorenamer")
        await bot.load_extension("cogs.privatevc")
        await bot.load_extension("cogs.feedback")
        await bot.load_extension("cogs.chatpolling")
        await bot.load_extension("cogs.modal")
        
        # ================= RUN BOT =================
        await bot.start(TOKEN)


# ================= START BOT =================
asyncio.run(main())
