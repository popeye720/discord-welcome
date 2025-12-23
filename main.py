import os
import discord
from discord.ext import commands
import asyncio
import wavelink

ALLOWED_GUILD_ID = 1137320194692370482  # 🔒 YOUR SERVER

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI")
LAVALINK_PASS = os.getenv("LAVALINK_PASS")

@bot.event
async def on_ready():
    print(f"✅ Bot Logged in as {bot.user}")

    # 🔒 Leave all unauthorized servers
    for guild in bot.guilds:
        if guild.id != ALLOWED_GUILD_ID:
            print(f"❌ Leaving unauthorized server: {guild.name}")
            await guild.leave()

    # 🔥 Lavalink connect
    if not wavelink.Pool.nodes:
        if not LAVALINK_URI or not LAVALINK_PASS:
            print("❌ Lavalink ENV vars missing")
            return

        await wavelink.Pool.connect(
            nodes=[
                wavelink.Node(
                    uri=LAVALINK_URI,
                    password=LAVALINK_PASS
                )
            ],
            client=bot
        )

        print("🎵 Lavalink connected successfully")

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        print(f"❌ Unauthorized server joined: {guild.name}")
        await guild.leave()

async def main():
    await bot.load_extension("cogs.welcome")
    await bot.load_extension("cogs.message")
    await bot.load_extension("cogs.autorole")
    await bot.load_extension("cogs.youtube")
    await bot.load_extension("cogs.ticket")
    await bot.load_extension("cogs.join_to_create")
    await bot.load_extension("cogs.auto_triggers")
    await bot.load_extension("cogs.free_games")
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.ChannelManager")
    await bot.load_extension("cogs.Embedder")
    await bot.load_extension("cogs.reactionRole")
    await bot.load_extension("cogs.clearmsg")
    await bot.load_extension("cogs.protection")
    await bot.load_extension("cogs.dm")
    await bot.load_extension("cogs.followuser")
    await bot.load_extension("cogs.stream")
    #await bot.load_extension("cogs.record")
    await bot.load_extension("cogs.clip")
    await bot.start(TOKEN)

asyncio.run(main())
