import discord
from discord.ext import commands, tasks
import aiohttp
import os

FREE_GAMES_CHANNEL = int(os.getenv("FREE_GAMES_CHANNEL"))
API_URL = "https://www.freetogame.com/api/giveaways"

class FreeGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.posted = set()

    async def cog_load(self):
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()

    @tasks.loop(minutes=1)  # 🔥 every 1 minute
    async def check_free_games(self):
        channel = self.bot.get_channel(FREE_GAMES_CHANNEL)
        if not channel:
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as resp:
                if resp.status != 200:
                    return
                games = await resp.json()

        for game in games:
            game_id = game["id"]
            if game_id in self.posted:
                continue

            self.posted.add(game_id)

            title = game["title"]
            platforms = game["platforms"]
            url = game["open_giveaway_url"]
            price = game.get("worth", "Unknown")
            end_date = game.get("end_date", "Limited Time")

            # 🎯 PLATFORM TAG
            if "Steam" in platforms:
                platform_tag = "Steam"
            elif "Epic" in platforms:
                platform_tag = "Epic Games"
            else:
                platform_tag = platforms

            # 🧾 FINAL MESSAGE (CARL-BOT STYLE)
            message = (
                f"🎮 **{title} ({platform_tag}) Giveaway**\n\n"
                f"💰 Price: ~~{price}~~ → **FREE**\n"
                f"⏰ Free Until: **{end_date}**\n\n"
                f"🔗 {url}"
            )

            await channel.send(message)

    @check_free_games.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(FreeGames(bot))
