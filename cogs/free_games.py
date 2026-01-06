import discord
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime
from database.models import freegames_col
import asyncio


class FreeGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.collection = freegames_col

        # indexes
        self.collection.create_index("guild_id", unique=True)

        self.session = aiohttp.ClientSession()

    async def cog_load(self):
        # start task only AFTER bot is ready
        await self.bot.wait_until_ready()
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()
        asyncio.create_task(self.session.close())

    # ===============================
    # ADMIN COMMANDS
    # ===============================

    @commands.command(name="freegames")
    @commands.has_guild_permissions(administrator=True)
    async def set_free_games(self, ctx, channel_id: int, role_id: int = None):

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        role = None
        if role_id:
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send("❌ Invalid role ID.")

        # 🔒 ONE CHANNEL PER SERVER
        existing = self.collection.find_one({"guild_id": ctx.guild.id})
        if existing:
            return await ctx.send(
                "❌ Free games already enabled in this server.\n"
                "Use `!removefg` first."
            )

        self.collection.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel_id,
            "role_id": role_id,
            "enabled": True,
            "last_posted": []
        })

        msg = f"✅ Free games enabled in {channel.mention}"
        if role:
            msg += f" with role ping {role.mention}"

        await ctx.send(msg)

    @commands.command(name="removefg")
    @commands.has_guild_permissions(administrator=True)
    async def remove_free_games(self, ctx):

        result = self.collection.delete_one({"guild_id": ctx.guild.id})
        if result.deleted_count == 0:
            return await ctx.send("❌ Free games not enabled in this server.")

        await ctx.send("✅ Free games updates disabled.")

    # ===============================
    # BACKGROUND TASK
    # ===============================

    @tasks.loop(hours=12)
    async def check_free_games(self):
        configs = list(self.collection.find({"enabled": True}))
        if not configs:
            return

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

            role_mention = ""
            if config.get("role_id"):
                role = guild.get_role(config["role_id"])
                if role:
                    role_mention = role.mention

            posted = config.get("last_posted", [])

            for game in all_games:
                if game["id"] in posted:
                    continue

                embed = discord.Embed(
                    title="🎮 FREE GAME ALERT",
                    color=0x00FFCC
                )
                embed.add_field(name="Game", value=game["title"], inline=False)
                embed.add_field(name="Platform", value=game["platform"], inline=False)
                embed.add_field(name="Free Till", value=game["free_till"], inline=False)

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Claim Now",
                        style=discord.ButtonStyle.link,
                        url=game["url"]
                    )
                )

                try:
                    await channel.send(
                        content=role_mention or None,
                        embed=embed,
                        view=view
                    )
                    await asyncio.sleep(1)  # rate-limit safety
                except discord.Forbidden:
                    continue

                posted.append(game["id"])

            # 🔒 LIMIT last_posted SIZE
            posted = posted[-100:]

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

        try:
            async with self.session.get(url, timeout=15) as resp:
                data = await resp.json()
        except Exception:
            return games

        elements = (
            data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )

        for game in elements:
            promotions = game.get("promotions")
            if not promotions:
                continue

            offers = promotions.get("promotionalOffers", [])
            if not offers:
                continue

            offer = offers[0]["promotionalOffers"][0]
            end = offer.get("endDate")
            if not end:
                continue

            if datetime.utcnow() > datetime.fromisoformat(end.replace("Z", "")):
                continue

            slug = game.get("productSlug") or game.get("urlSlug")
            if not slug:
                continue

            games.append({
                "id": game["id"],
                "title": game["title"],
                "platform": "Epic Games",
                "free_till": end.split("T")[0],
                "url": f"https://store.epicgames.com/p/{slug}"
            })

        return games

    async def fetch_steam_games(self):
        url = "https://store.steampowered.com/api/featuredcategories"
        games = []

        try:
            async with self.session.get(url, timeout=15) as resp:
                data = await resp.json()
        except Exception:
            return games

        for item in data.get("specials", {}).get("items", []):
            if item.get("discount_percent") != 100:
                continue

            # extra safety: skip free weekends
            if not item.get("is_free"):
                continue

            games.append({
                "id": str(item["id"]),
                "title": item["name"],
                "platform": "Steam",
                "free_till": "Limited Time",
                "url": f"https://store.steampowered.com/app/{item['id']}"
            })

        return games


async def setup(bot):
    await bot.add_cog(FreeGames(bot))
