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
        online = sum(
            1 for m in guild.members
            if not m.bot and m.status != discord.Status.offline
        )

        member_vc = await guild.create_voice_channel(
            name=f"👥 Members: {members}", category=category
        )

        bot_vc = await guild.create_voice_channel(
            name=f"🤖 Bots: {bots}", category=category
        )

        online_vc = await guild.create_voice_channel(
            name=f"🟢 Online: {online}", category=category
        )

        for vc in (member_vc, bot_vc, online_vc):
            await vc.set_permissions(guild.default_role, connect=False)

        serverstats_col.insert_one({
            "guild_id": guild.id,
            "category_id": category.id,
            "member_vc_id": member_vc.id,
            "bot_vc_id": bot_vc.id,
            "online_vc_id": online_vc.id
        })

        await ctx.reply("✅ Server stats setup completed!")

    # -------- ENSURE (ONLY RECREATE IF DELETED) --------
    async def ensure_channels(self, guild: discord.Guild):
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return

        category = guild.get_channel(data["category_id"])
        member_vc = guild.get_channel(data["member_vc_id"])
        bot_vc = guild.get_channel(data["bot_vc_id"])
        online_vc = guild.get_channel(data.get("online_vc_id"))

        if not category:
            category = await guild.create_category("📊 Server Stats")
            await category.edit(position=0)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"category_id": category.id}}
            )

        members = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        online = sum(
            1 for m in guild.members
            if not m.bot and m.status != discord.Status.offline
        )

        if not member_vc:
            member_vc = await guild.create_voice_channel(
                f"👥 Members: {members}", category=category
            )
            await member_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"member_vc_id": member_vc.id}}
            )

        if not bot_vc:
            bot_vc = await guild.create_voice_channel(
                f"🤖 Bots: {bots}", category=category
            )
            await bot_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"bot_vc_id": bot_vc.id}}
            )

        if not online_vc:
            online_vc = await guild.create_voice_channel(
                f"🟢 Online: {online}", category=category
            )
            await online_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"online_vc_id": online_vc.id}}
            )

    # -------- UPDATE COUNTS --------
    async def update_stats(self, guild: discord.Guild):
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return

        await self.ensure_channels(guild)

        member_vc = guild.get_channel(data["member_vc_id"])
        bot_vc = guild.get_channel(data["bot_vc_id"])
        online_vc = guild.get_channel(data.get("online_vc_id"))

        if not member_vc or not bot_vc or not online_vc:
            return

        members = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        online = sum(
            1 for m in guild.members
            if not m.bot and m.status != discord.Status.offline
        )

        try:
            await member_vc.edit(name=f"👥 Members: {members}")
            await bot_vc.edit(name=f"🤖 Bots: {bots}")
            await online_vc.edit(name=f"🟢 Online: {online}")
        except discord.HTTPException:
            pass

    # -------- EVENTS --------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.update_stats(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.update_stats(member.guild)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.guild:
            await self.update_stats(before.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        data = serverstats_col.find_one({"guild_id": channel.guild.id})
        if not data:
            return

        if channel.id in (
            data["category_id"],
            data["member_vc_id"],
            data["bot_vc_id"],
            data.get("online_vc_id")
        ):
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

        serverstats_col.delete_one({"guild_id": guild.id})

        for cid in (
            "member_vc_id",
            "bot_vc_id",
            "online_vc_id",
            "category_id"
        ):
            ch = guild.get_channel(data.get(cid))
            if ch:
                try:
                    await ch.delete()
                except discord.Forbidden:
                    pass

        await ctx.reply("✅ Server stats system deleted successfully.")


async def setup(bot):
    await bot.add_cog(ServerStats(bot))
