import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from datetime import datetime
from database.models import freegames_col
import asyncio
import time
from utils.embed_color import create_embed

CLEANUP_AFTER_SECONDS = 60 * 60 * 24 * 7  # 7 DAYS

# ================= COG =================
class FreeGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.collection = freegames_col
        try:
            self.collection.create_index("guild_id", unique=True)
        except Exception as e:
            print("Index error:", e)
        self.session: aiohttp.ClientSession | None = None

    # =============================== COG LOAD/UNLOAD ===============================
    async def cog_load(self):
        self.check_free_games.start()
        print("✅ FreeGames cog loaded")

    async def cog_unload(self):
        self.check_free_games.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
        print("❌ FreeGames cog unloaded")

    # =============================== ADMIN CHECK ===============================
    def can_manage(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.guild
            and (
                interaction.user.id == interaction.guild.owner_id
                or interaction.user.guild_permissions.administrator
            )
        )

    # =============================== SLASH COMMANDS ===============================
    @app_commands.command(
        name="freegames_enable",
        description="Enable free games alerts in a channel"
    )
    @app_commands.describe(
        channel="Channel to post free games",
        role="Optional role to mention"
    )
    async def freegames_enable(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role | None = None
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.", ephemeral=True
            )

        if self.collection.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "❌ Free games already enabled. Use `/freegames_disable` first.", ephemeral=True
            )

        self.collection.insert_one({
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "role_id": role.id if role else None,
            "enabled": True,
            "last_posted": []
        })

        msg = f"✅ Free games enabled in {channel.mention}"
        if role:
            msg += f" with role ping {role.mention}"

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="freegames_disable",
        description="Disable free games alerts"
    )
    async def freegames_disable(self, interaction: discord.Interaction):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.", ephemeral=True
            )

        result = self.collection.delete_one({"guild_id": interaction.guild.id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "❌ Free games not enabled.", ephemeral=True
            )

        await interaction.response.send_message("✅ Free games updates disabled.", ephemeral=True)

    @app_commands.command(
        name="freegames_force",
        description="Force a free games check now"
    )
    async def freegames_force(self, interaction: discord.Interaction):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.", ephemeral=True
            )

        # Send initial ephemeral response
        await interaction.response.send_message("🔄 Free games check started...", ephemeral=True)

        async def run_force_check():
            configs = list(self.collection.find({"enabled": True}))
            total_posted = 0

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

                posted_before = len(config.get("last_posted", []))
                await self.run_free_games()  # Run the main logic
                config_after = self.collection.find_one({"guild_id": config["guild_id"]})
                posted_after = len(config_after.get("last_posted", []))
                total_posted += max(0, posted_after - posted_before)

            await interaction.followup.send(
                f"✅ Free games check completed. {total_posted} new game(s) posted.",
                ephemeral=True
            )

        # Run the force check as a background task
        asyncio.create_task(run_force_check())

    # =============================== BACKGROUND TASK ===============================
    @tasks.loop(hours=12)
    async def check_free_games(self):
        await self.run_free_games()

    @check_free_games.before_loop
    async def before_free_games(self):
        await self.bot.wait_until_ready()

    # =============================== CORE LOGIC ===============================
    async def run_free_games(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

        configs = list(self.collection.find({"enabled": True}))
        if not configs:
            return

        epic_games = await self.fetch_epic_games()
        now = time.time()

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
            # Clean old entries
            posted = [p for p in posted if isinstance(p, dict) and now - p["ts"] < CLEANUP_AFTER_SECONDS]
            posted_ids = {p["id"] for p in posted}

            for game in epic_games:
                if game["id"] in posted_ids:
                    continue

                embed = create_embed(title="🎮 FREE GAME ALERT")
                embed.add_field(name="Game", value=game["title"], inline=False)
                embed.add_field(name="Platform", value=game["platform"], inline=False)
                embed.add_field(name="Free Till", value=game["free_till"], inline=False)

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Claim Now", style=discord.ButtonStyle.link, url=game["url"]))

                try:
                    await channel.send(content=role_mention or None, embed=embed, view=view)
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    continue

                posted.append({"id": game["id"], "ts": now})

            self.collection.update_one({"guild_id": guild.id}, {"$set": {"last_posted": posted}})

    # =============================== DATA FETCHERS ===============================
    async def fetch_epic_games(self):
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        games = []

        try:
            async with self.session.get(url, timeout=15) as resp:
                data = await resp.json()
        except Exception as e:
            print("Epic error:", e)
            return games

        elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
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

            # ===== UPDATED LINK LOGIC =====
            claim_url = None
            mappings = game.get("catalogNs", {}).get("mappings", [])
            for m in mappings:
                slug = m.get("pageSlug")
                if slug:
                    claim_url = f"https://www.epicgames.com/store/p/{slug}"
                    break
            if not claim_url:
                url_slug = game.get("urlSlug")
                if url_slug:
                    claim_url = f"https://www.epicgames.com/store/p/{url_slug}"

            if not claim_url:
                continue  # skip if no working URL

            games.append({
                "id": game["id"],
                "title": game["title"],
                "platform": "Epic Games",
                "free_till": end.split("T")[0],
                "url": claim_url
            })

        return games

# =============================== SETUP ===============================
async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGames(bot))
