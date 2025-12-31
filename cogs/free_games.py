import discord
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime
from database.mongo import get_db

class FreeGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.collection = self.db.free_games_config
        self.check_free_games.start()

        self.collection.create_index("guild_id")
        self.collection.create_index([("guild_id", 1), ("channel_id", 1)])

    def cog_unload(self):
        self.check_free_games.cancel()

    # ===============================
    # ADMIN COMMANDS
    # ===============================

    @commands.command(name="freegames")
    @commands.has_guild_permissions(administrator=True)
    async def set_free_games(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid channel ID.")

        self.collection.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {
                "channel_id": channel_id,
                "enabled": True,
                "last_posted": []
            }},
            upsert=True
        )

        await ctx.send(f"Free games updates enabled in {channel.mention}")

    @commands.command(name="removefg")
    @commands.has_guild_permissions(administrator=True)
    async def remove_free_games(self, ctx):
        self.collection.delete_one({"guild_id": ctx.guild.id})
        await ctx.send("Free games updates disabled.")

    # ===============================
    # BACKGROUND TASK
    # ===============================

    @tasks.loop(hours=12)
    async def check_free_games(self):
        configs = self.collection.find({"enabled": True})

        epic_games = await self.fetch_epic_games()
        steam_games = await self.fetch_steam_games()

        all_games = epic_games + steam_games

        for config in configs:
            guild = self.bot.get_guild(config["guild_id"])
            if not guild:
                continue

            channel = guild.get_channel(config["channel_id"])
            if not channel:
                continue

            posted = config.get("last_posted", [])

            for game in all_games:
                if game["id"] in posted:
                    continue

                embed = discord.Embed(
                    title="🎮 FREE GAME ALERT",
                    color=0x00ffcc
                )
                embed.add_field(name="Game Title", value=game["title"], inline=False)
                embed.add_field(name="Platform", value=game["platform"], inline=False)
                embed.add_field(name="Previous Price", value=game["price"], inline=False)
                embed.add_field(name="Free Till", value=game["free_till"], inline=False)

                await channel.send(embed=embed)

                posted.append(game["id"])

            self.collection.update_one(
                {"guild_id": guild.id},
                {"$set": {"last_posted": posted}}
            )

    # ===============================
    # DATA FETCHERS
    # ===============================

    async def fetch_epic_games(self):
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        games = []

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        elements = data["data"]["Catalog"]["searchStore"]["elements"]

        for game in elements:
            promotions = game.get("promotions")
            if not promotions:
                continue

            for promo in promotions.get("promotionalOffers", []):
                start = promo["promotionalOffers"][0]["startDate"]
                end = promo["promotionalOffers"][0]["endDate"]

                if datetime.utcnow() > datetime.fromisoformat(end.replace("Z", "")):
                    continue

                games.append({
                    "id": game["id"],
                    "title": game["title"],
                    "platform": "Epic Games",
                    "price": "$" + str(game["price"]["totalPrice"]["originalPrice"] / 100),
                    "free_till": end.split("T")[0]
                })

        return games

    async def fetch_steam_games(self):
        # Steam does not provide official free games API
        # Using SteamDB-like filtering (safe fallback)

        url = "https://store.steampowered.com/api/featuredcategories"
        games = []

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        for item in data.get("specials", {}).get("items", []):
            if item["discount_percent"] == 100:
                games.append({
                    "id": str(item["id"]),
                    "title": item["name"],
                    "platform": "Steam",
                    "price": "$" + str(item["original_price"] / 100),
                    "free_till": "Limited Time"
                })

        return games


async def setup(bot):
    await bot.add_cog(FreeGames(bot))
