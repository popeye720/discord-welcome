import discord
from discord.ext import commands
from discord import app_commands
from database.models import serverstats_col


class ServerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK (ADMIN / OWNER) -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ----------------- /server-stats -----------------
    @app_commands.command(name="server-stats", description="Setup server stats voice channels (Admin/Owner only)")
    async def server_stats(self, interaction: discord.Interaction):
        # ref code jaisa: silently ignore (no leak) if no perms
        if not await self.is_admin_or_owner(interaction):
            return

        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

        # already set?
        if serverstats_col.find_one({"guild_id": guild.id}):
            return await interaction.response.send_message(
                "⚠️ Server stats already set.",
                ephemeral=True
            )

        # create category + channels
        try:
            category = await guild.create_category("📊 Server Stats")
            await category.edit(position=0)

            members = len(guild.members)
            bots = sum(1 for m in guild.members if m.bot)
            online = sum(1 for m in guild.members if m.status != discord.Status.offline)

            member_vc = await guild.create_voice_channel(f"Members: {members}", category=category)
            bot_vc = await guild.create_voice_channel(f"Bots: {bots}", category=category)
            online_vc = await guild.create_voice_channel(f"Online: {online}", category=category)

            for vc in (member_vc, bot_vc, online_vc):
                await vc.set_permissions(guild.default_role, connect=False)

            serverstats_col.insert_one({
                "guild_id": guild.id,
                "category_id": category.id,
                "member_vc_id": member_vc.id,
                "bot_vc_id": bot_vc.id,
                "online_vc_id": online_vc.id
            })

            await interaction.response.send_message("✅ Server stats setup completed!", ephemeral=True)

        except discord.Forbidden:
            # if no perms mid-way
            try:
                await interaction.response.send_message(
                    "❌ I don't have enough permissions (Manage Channels).",
                    ephemeral=True
                )
            except:
                pass
        except discord.HTTPException as e:
            try:
                await interaction.response.send_message(f"❌ Discord error: `{e}`", ephemeral=True)
            except:
                pass

    # -------- ENSURE (ONLY RECREATE IF DELETED) --------
    async def ensure_channels(self, guild: discord.Guild):
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return

        category = guild.get_channel(data.get("category_id"))
        member_vc = guild.get_channel(data.get("member_vc_id"))
        bot_vc = guild.get_channel(data.get("bot_vc_id"))
        online_vc = guild.get_channel(data.get("online_vc_id"))

        # counts
        members = len(guild.members)
        bots = sum(1 for m in guild.members if m.bot)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        # category recreate
        if not category:
            category = await guild.create_category("📊 Server Stats")
            await category.edit(position=0)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"category_id": category.id}}
            )

        # member vc recreate
        if not member_vc:
            member_vc = await guild.create_voice_channel(f"👥 Members: {members}", category=category)
            await member_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"member_vc_id": member_vc.id}}
            )

        # bot vc recreate
        if not bot_vc:
            bot_vc = await guild.create_voice_channel(f"Bots: {bots}", category=category)
            await bot_vc.set_permissions(guild.default_role, connect=False)
            serverstats_col.update_one(
                {"guild_id": guild.id},
                {"$set": {"bot_vc_id": bot_vc.id}}
            )

        # online vc recreate
        if not online_vc:
            online_vc = await guild.create_voice_channel(f"Online: {online}", category=category)
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

        # recreate missing items if deleted
        try:
            await self.ensure_channels(guild)
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return

        # re-fetch latest ids (ensure_channels might have updated ids)
        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return

        member_vc = guild.get_channel(data.get("member_vc_id"))
        bot_vc = guild.get_channel(data.get("bot_vc_id"))
        online_vc = guild.get_channel(data.get("online_vc_id"))

        if not member_vc or not bot_vc or not online_vc:
            return

        members = len(guild.members)
        bots = sum(1 for m in guild.members if m.bot)
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        try:
            await member_vc.edit(name=f"👥 Members: {members}")
            await bot_vc.edit(name=f"Bots: {bots}")
            await online_vc.edit(name=f"Online: {online}")
        except discord.HTTPException:
            pass

    # -------- EVENTS --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.update_stats(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.update_stats(member.guild)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        # presence update a lot spam hota hai, but keep same core logic
        if before.guild:
            await self.update_stats(before.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        data = serverstats_col.find_one({"guild_id": channel.guild.id})
        if not data:
            return

        if channel.id in (
            data.get("category_id"),
            data.get("member_vc_id"),
            data.get("bot_vc_id"),
            data.get("online_vc_id"),
        ):
            await self.update_stats(channel.guild)

    # -------- RESTART SAFE --------
    @commands.Cog.listener()
    async def on_ready(self):
        for data in serverstats_col.find({}, {"guild_id": 1}):
            guild = self.bot.get_guild(data.get("guild_id"))
            if guild:
                await self.update_stats(guild)

    # ----------------- /del-serverstats -----------------
    @app_commands.command(name="del-serverstats", description="Delete server stats system (Admin/Owner only)")
    async def del_serverstats(self, interaction: discord.Interaction):
        # ref code jaisa: silently ignore (no leak) if no perms
        if not await self.is_admin_or_owner(interaction):
            return

        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

        data = serverstats_col.find_one({"guild_id": guild.id})
        if not data:
            return await interaction.response.send_message(
                "❌ Server stats system is not set.",
                ephemeral=True
            )

        # delete db first (same as your code)
        serverstats_col.delete_one({"guild_id": guild.id})

        # delete channels/category
        for cid in ("member_vc_id", "bot_vc_id", "online_vc_id", "category_id"):
            ch = guild.get_channel(data.get(cid))
            if ch:
                try:
                    await ch.delete()
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

        await interaction.response.send_message(
            "✅ Server stats system deleted successfully.",
            ephemeral=True
        )

    # ----------------- GLOBAL CHECK (optional like ref code) -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerStats(bot))
