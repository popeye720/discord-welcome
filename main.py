import os
import discord
from discord.ext import commands
import asyncio
import wavelink

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

    # 🔥 Lavalink connect (safe check)
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
    await bot.start(TOKEN)

asyncio.run(main())
