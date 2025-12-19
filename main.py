import os
import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True   # 🔥 REQUIRED FOR on_member_join

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")

@bot.event
async def on_ready():
    print(f"✅ Bot Logged in as {bot.user}")

async def main():
    await bot.load_extension("cogs.welcome")
    await bot.load_extension("cogs.message")
    await bot.load_extension("cogs.autorole")
    #await bot.load_extension("cogs.safety")
    await bot.load_extension("cogs.ticket")
    await bot.start(TOKEN)

asyncio.run(main())
