import discord
from discord.ext import commands, tasks
import feedparser
import os

FREE_GAMES_CHANNEL = int(os.getenv("FREE_GAMES_CHANNEL"))

# ===== OFFICIAL RSS FEEDS =====
EPIC_RSS = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
STEAM_RSS = "https://store.steampowered.com/feeds/news.xml"

class FreeGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.posted_links = set()

    async def cog_load(self):
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()

    # 🔥 every 30 minutes (Carl-bot style, safe)
    @tasks.loop(minutes=30)
    async def check_free_games(self):
        channel = self.bot.get_channel(FREE_GAMES_CHANNEL)
        if not channel:
            return

        # ========= EPIC GAMES =========
        epic = feedparser.parse(EPIC_RSS)

        for game in epic.entries:
            link = game.get("link")
            title = game.get("title")

            if not link or link in self.posted_links:
                continue

            self.posted_links.add(link)

            embed = discord.Embed(
                title="🎮 FREE GAME (Epic Games)",
                description=f"**{title}** is now **FREE** on Epic Games Store!",
                color=discord.Color.green()
            )
            embed.add_field(name="Platform", value="Epic Games", inline=True)
            embed.add_field(name="Price", value="~~Paid~~ → **FREE**", inline=True)
            embed.add_field(name="Claim Here", value=f"[Click to Claim]({link})", inline=False)

            await channel.send(embed=embed)

        # ========= STEAM =========
        steam = feedparser.parse(STEAM_RSS)

        for entry in steam.entries:
            title = entry.get("title", "")
            link = entry.get("link")

            # Steam free keywords (Carl-bot logic)
            if (
                "Free" not in title
                or not link
                or link in self.posted_links
            ):
                continue

            self.posted_links.add(link)

            embed = discord.Embed(
                title="🎮 FREE GAME (Steam)",
                description=title,
                color=discord.Color.blue()
            )
            embed.add_field(name="Platform", value="Steam", inline=True)
            embed.add_field(name="Link", value=f"[View on Steam]({link})", inline=False)

            await channel.send(embed=embed)

    @check_free_games.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(FreeGames(bot))
