import discord
from discord.ext import commands
from discord import Embed
import asyncio
from googlesearch import search  # pip install google
from database.models import search_col  # DB collection for setup

class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.search_locks = {}

    async def get_guild_lock(self, guild_id: str):
        if guild_id not in self.search_locks:
            self.search_locks[guild_id] = asyncio.Lock()
        return self.search_locks[guild_id]

    # -------- PERMISSION CHECK --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SETUP COMMAND --------
    @commands.command(name="setupsearch")
    @is_admin()
    async def setup_search(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID")

        # Check if already setup
        existing = search_col.find_one({"guild_id": ctx.guild.id})
        if existing:
            return await ctx.reply("⚠️ Search is already setup. Use `!disablesearch` first.")

        search_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel_id
        })

        await ctx.reply(f"✅ Search setup complete in {channel.mention}")

    # -------- DISABLE COMMAND --------
    @commands.command(name="disablesearch")
    @is_admin()
    async def disable_search(self, ctx):
        result = search_col.find_one_and_delete({"guild_id": ctx.guild.id})
        if not result:
            return await ctx.reply("⚠️ Search is not setup yet.")
        await ctx.reply(f"✅ Search disabled for **{ctx.guild.name}**.")

    # -------- SEARCH COMMAND --------
    @commands.command(name="search")
    async def search_command(self, ctx, *, query: str):
        # Get setup channel
        data = search_col.find_one({"guild_id": ctx.guild.id})
        if not data:
            return await ctx.reply("⚠️ Search is not setup yet. Admin must run `!setupsearch <channel>`.")

        setup_channel_id = data["channel_id"]

        # Wrong channel
        if ctx.channel.id != setup_channel_id:
            if ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id:
                # Allow admins anywhere, just warn
                await ctx.reply(f"⚠️ Admin {ctx.author.mention}, please note search is normally restricted to <#{setup_channel_id}>.")
            else:
                # Normal user -> delete both messages
                warn = await ctx.reply(f"⚠️ {ctx.author.mention}, use <#{setup_channel_id}> for search.")
                await asyncio.sleep(2)
                await ctx.message.delete()
                await warn.delete()
                return

        lock = await self.get_guild_lock(ctx.guild.id)
        if lock.locked():
            return await ctx.reply("⏳ Another search is in progress. Please wait.")

        async with lock:
            status = await ctx.reply(f"🔍 Searching for: `{query}` …")

            try:
                # Search top 5 results
                results = []
                for url in search(query, num_results=5):
                    results.append(url)

                if not results:
                    return await status.edit(content="❌ No results found.")

                # Prepare Embed
                embed = Embed(
                    title=f"🔎 Search results for: {query}",
                    color=discord.Color.blue()
                )

                for i, url in enumerate(results, start=1):
                    if len(url) > 100:
                        url = url[:100] + "..."
                    embed.add_field(name=f"{i}.", value=url, inline=False)

                await status.edit(content=None, embed=embed)

            except Exception as e:
                await status.edit(content=f"❌ Search failed: `{e}`")

# -------- SETUP FUNCTION FOR BOT --------
async def setup(bot):
    await bot.add_cog(Search(bot))
