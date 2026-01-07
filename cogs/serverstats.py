import discord
from discord.ext import commands
from database.models import serverstats_col


class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- ADMIN / OWNER CHECK --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SETUP SERVER STATS --------
    @commands.command(name="serverstats")
    @is_admin()
    async def serverstats(self, ctx):
        guild = ctx.guild

        if serverstats_col.find_one({"guild_id": guild.id}):
            return await ctx.reply("⚠️ Server stats already set.")

        category = await guild.create_category(name="📊 Server Stats")
        await category.edit(position=0)

        members = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)

        member_vc = await guild.create_voice_channel(
            name=f"👥 Members: {members}",
            category=category
        )

        bot_vc = await guild.create_voice_channel(
            name=f"🤖 Bots: {bots}",
            category=category
        )

        for vc in (member_vc, bot_vc):
            await vc.set_permissions(guild.default_role, connect=False)

        serverstats_col.insert_one({
            "guild_id": guild.id,
            "category_id": category.id,
            "member_vc_id": member_vc.id,
            "bot_vc_id": bot_vc.id
        })

        await ctx.reply("✅ Server stats setup completed!")

    # -------- ENSURE / SELF HEAL --------
    async def ensure_channels(self, guild: discord.Guild):
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return

        category = guild.get_channel(data["category_id"])
        member_vc = guild.get_channel(data["member_vc_id"])
        bot_vc = guild.get_channel(data["bot_vc_id"])

        # Recreate category if deleted
        if not category:
            category = await guild.create_category("📊 Server Stats")
            await category.edit(position=0)

        members = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)

        # Recreate member VC
        if not member_vc:
            member_vc = await guild.create_voice_channel(
                name=f"👥 Members: {members}",
                category=category
            )
            await member_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"member_vc_id": member_vc.id}}
            )

        # Recreate bot VC
        if not bot_vc:
            bot_vc = await guild.create_voice_channel(
                name=f"🤖 Bots: {bots}",
                category=category
            )
            await bot_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"bot_vc_id": bot_vc.id}}
            )

        return category, member_vc, bot_vc

    # -------- UPDATE COUNTS (AUTO RENAME FIX) --------
    async def update_stats(self, guild: discord.Guild):
        result = await self.ensure_channels(guild)
        if not result:
            return

        _, member_vc, bot_vc = result

        members = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)

        try:
            if member_vc.name != f"👥 Members: {members}":
                await member_vc.edit(name=f"👥 Members: {members}")

            if bot_vc.name != f"🤖 Bots: {bots}":
                await bot_vc.edit(name=f"🤖 Bots: {bots}")
        except discord.HTTPException:
            pass

    # -------- AUTO UPDATE EVENTS --------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.update_stats(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.update_stats(member.guild)

    # -------- IF VC OR CATEGORY DELETED --------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel.guild, discord.Guild):
            return
        await self.update_stats(channel.guild)

    # -------- RESTART SAFE --------
    @commands.Cog.listener()
    async def on_ready(self):
        for data in serverstats_col.find({}, {"guild_id": 1}):
            guild = self.bot.get_guild(data["guild_id"])
            if guild:
                await self.update_stats(guild)

    # -------- DELETE SERVER STATS --------
    @commands.command(name="delserverstats")
    @is_admin()
    async def delserverstats(self, ctx):
        guild = ctx.guild
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return await ctx.reply("❌ Server stats system is not set.")

        for cid in ("member_vc_id", "bot_vc_id", "category_id"):
            ch = guild.get_channel(data.get(cid))
            if ch:
                try:
                    await ch.delete()
                except discord.Forbidden:
                    pass

        serverstats_col.delete_one({"guild_id": guild.id})
        await ctx.reply("✅ Server stats system deleted successfully.")


async def setup(bot):
    await bot.add_cog(ServerStats(bot))
