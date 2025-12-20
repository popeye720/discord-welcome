import os
import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")

@bot.event
async def on_ready():
    print(f"✅ Bot Logged in as {bot.user}")

async def main():
    await bot.load_extension("cogs.welcome")
    await bot.load_extension("cogs.message")
    await bot.load_extension("cogs.autorole")
    await bot.load_extension("cogs.youtube")
    await bot.load_extension("cogs.ticket")
    await bot.start(TOKEN)

asyncio.run(main())
