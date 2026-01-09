import discord
from discord.ext import commands
from discord import app_commands, Embed
import asyncio
import time
from ddgs import DDGS
from database.models import search_col  # MongoDB collection

NSFW_KEYWORDS = [
    "sex","porn","xxx","nude","boobs","vagina","penis",
    "anal","blowjob","hentai","nsfw","onlyfans"
]

SEARCH_COOLDOWN = 10  # seconds per server

class Search(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_locks = {}
        self.guild_cooldowns = {}

    # ----------------- LOCK -----------------
    def get_guild_lock(self, gid: int):
        if gid not in self.guild_locks:
            self.guild_locks[gid] = asyncio.Lock()
        return self.guild_locks[gid]

    # ----------------- PERMISSION CHECK -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction):
        guild: discord.Guild = interaction.guild
        if guild is None:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ----------------- SETUP SEARCH -----------------
    @app_commands.command(name="setupsearch", description="Setup the search channel")
    async def setupsearch(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only server owner or admins can use this.", ephemeral=True
            )

        guild_id = interaction.guild.id
        search_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"search_channel": channel.id, "search_channel_name": channel.name}},
            upsert=True
        )
        await interaction.response.send_message(
            f"✅ Search enabled in {channel.mention}", ephemeral=True
        )

    # ----------------- DISABLE SEARCH -----------------
    @app_commands.command(name="disablesearch", description="Disable the search system")
    async def disablesearch(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only server owner or admins can use this.", ephemeral=True
            )

        guild_id = interaction.guild.id
        result = search_col.delete_one({"guild_id": guild_id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "⚠️ Search was not setup.", ephemeral=True
            )

        await interaction.response.send_message("✅ Search disabled", ephemeral=True)

    # ----------------- SEARCH COMMAND -----------------
    @app_commands.command(name="search", description="Search the web")
    async def search(self, interaction: discord.Interaction, query: str):
        # NSFW check
        if any(word in query.lower() for word in NSFW_KEYWORDS):
            return await interaction.response.send_message(
                "🚫 NSFW searches are not allowed.", ephemeral=True
            )

        guild_id = interaction.guild.id
        guild_data = search_col.find_one({"guild_id": guild_id})
        if not guild_data or "search_channel" not in guild_data:
            return await interaction.response.send_message(
                "⚠️ Search not setup on this server.", ephemeral=True
            )

        search_channel_id = guild_data["search_channel"]
        if interaction.channel.id != search_channel_id:
            return await interaction.response.send_message(
                f"⚠️ Use <#{search_channel_id}> for search.", ephemeral=True
            )

        # cooldown
        now = time.time()
        last = self.guild_cooldowns.get(guild_id, 0)
        if now - last < SEARCH_COOLDOWN:
            return await interaction.response.send_message(
                f"⏳ Wait {int(SEARCH_COOLDOWN - (now-last))}s", ephemeral=True
            )
        self.guild_cooldowns[guild_id] = now

        await interaction.response.defer()
        lock = self.get_guild_lock(guild_id)
        async with lock:
            results = []
            image_url = None
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    results.append(r)
                for img in ddgs.images(query, max_results=1):
                    image_url = img.get("image")
                    break

            if not results:
                return await interaction.followup.send("❌ No results found")

            embed = Embed(title=f"🔎 {query}", color=discord.Color.blue())
            for i, r in enumerate(results, 1):
                snippet = r.get("body", "")[:180]
                embed.add_field(
                    name=f"{i}. {r.get('title','No title')}",
                    value=f"{snippet}...\n🔗 {r.get('href','')}",
                    inline=False
                )
            if image_url:
                embed.set_image(url=image_url)
            embed.set_footer(text="Powered by Tejas")
            await interaction.followup.send(embed=embed)

# ----------------- COG SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))
    # ⚠️ No bot.tree.add_command() calls here
