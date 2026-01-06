import os
import discord
from discord.ext import commands
import asyncio

# ✅ ALLOWED SERVERS
ALLOWED_GUILD_IDS = {
    1137320194692370482,
    1455284985807503443
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")


@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    # 🔥 REGISTER PERSISTENT VIEWS (MOST IMPORTANT)
    from cogs.ticket import TicketButton, CloseTicketView
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())

    # leave unauthorized servers
    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILD_IDS:
            print(f"Leaving unauthorized server: {guild.name}")
            await guild.leave()


@bot.event
async def on_guild_join(guild):
    if guild.id not in ALLOWED_GUILD_IDS:
        print(f"Unauthorized server joined: {guild.name}")
        await guild.leave()


async def main():
    async with bot:
        #await bot.load_extension("cogs.welcome")
        await bot.load_extension("cogs.message")
        #await bot.load_extension("cogs.autorole")
        #await bot.load_extension("cogs.youtube")
        await bot.load_extension("cogs.ticket")
        await bot.load_extension("cogs.join_to_create")
        await bot.load_extension("cogs.auto_triggers")
        await bot.load_extension("cogs.free_games")
        await bot.load_extension("cogs.ChannelManager")
        await bot.load_extension("cogs.Embedder")
        await bot.load_extension("cogs.reactionRole")
        await bot.load_extension("cogs.antilinks")
        await bot.load_extension("cogs.dm")
        await bot.load_extension("cogs.followuser")
        await bot.load_extension("cogs.streammode")
        await bot.load_extension("cogs.clip")
        await bot.load_extension("cogs.antispam")
        await bot.load_extension("cogs.moderation")
        await bot.load_extension("cogs.joinleave")
        #await bot.load_extension("cogs.voice_speak")
        await bot.start(TOKEN)


asyncio.run(main())
