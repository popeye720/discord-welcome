import discord
from discord.ext import commands
from database.models import jtc_col


class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}   # vc_id : creator_id
        self._ready_done = False  # on_ready guard

    # ================= PERMISSION CHECK =================
    def can_manage(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    # ================= BOT READY =================
    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_done:
            return

        self._ready_done = True

        for guild in self.bot.guilds:
            await self.setup_jtc(guild)

    async def setup_jtc(self, guild: discord.Guild):
        conf = jtc_col.find_one({"guild_id": guild.id})
        if not conf:
            return

        category = guild.get_channel(conf.get("category_id"))
        if not isinstance(category, discord.CategoryChannel):
            return

        # delete old JTC safely
        old_channel = guild.get_channel(conf.get("jtc_channel_id"))
        if isinstance(old_channel, discord.VoiceChannel):
            try:
                await old_channel.delete()
            except Exception:
                pass

        # create fresh JTC channel
        channel = await guild.create_voice_channel(
            name="Join to Create",
            category=category
        )

        jtc_col.update_one(
            {"guild_id": guild.id},
            {"$set": {"jtc_channel_id": channel.id}}
        )

    # ================= CREATE JTC =================
    @commands.command(name="createjtc")
    async def create_jtc(self, ctx, category_id: int):
        if not self.can_manage(ctx):
            return await ctx.reply(
                "You do not have permission to use this command."
            )

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.reply("Invalid category ID.")

        # delete existing JTC if present
        old = jtc_col.find_one({"guild_id": ctx.guild.id})
        if old:
            old_vc = ctx.guild.get_channel(old.get("jtc_channel_id"))
            if isinstance(old_vc, discord.VoiceChannel):
                try:
                    await old_vc.delete()
                except Exception:
                    pass

        channel = await ctx.guild.create_voice_channel(
            name="Join to Create",
            category=category
        )

        jtc_col.update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "category_id": category.id,
                    "jtc_channel_id": channel.id
                }
            },
            upsert=True
        )

        await ctx.reply(
            f"Join-to-Create voice channel has been created in category: {category.name}"
        )

    # ================= DELETE JTC =================
    @commands.command(name="deletejtc")
    async def delete_jtc(self, ctx, jtc_channel_id: int):
        if not self.can_manage(ctx):
            return await ctx.reply(
                "You do not have permission to use this command."
            )

        conf = jtc_col.find_one({"guild_id": ctx.guild.id})
        if not conf:
            return await ctx.reply(
                "Join-to-Create has not been set up for this server."
            )

        if conf.get("jtc_channel_id") != jtc_channel_id:
            return await ctx.reply(
                "The provided channel ID does not match the active Join-to-Create channel."
            )

        channel = ctx.guild.get_channel(jtc_channel_id)
        if isinstance(channel, discord.VoiceChannel):
            try:
                await channel.delete()
            except Exception:
                pass

        jtc_col.delete_one({"guild_id": ctx.guild.id})

        await ctx.reply(
            "Join-to-Create system has been disabled and the channel has been deleted."
        )

    # ================= VOICE LISTENER =================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conf = jtc_col.find_one({"guild_id": member.guild.id})
        if not conf:
            return

        jtc_id = conf.get("jtc_channel_id")

        # user joined JTC
        if after.channel and after.channel.id == jtc_id:
            guild = member.guild
            category = after.channel.category

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(
                    connect=True,
                    manage_channels=True,
                    move_members=True
                )
            }

            vc = await guild.create_voice_channel(
                name=f"{member.name}'s VC",
                category=category,
                overwrites=overwrites
            )

            await member.move_to(vc)
            self.temp_channels[vc.id] = member.id

        # delete empty temporary VC
        if before.channel and before.channel.id in self.temp_channels:
            vc = before.channel

            if not vc.members:
                try:
                    await vc.delete()
                except Exception:
                    pass

                self.temp_channels.pop(vc.id, None)

    # ================= CLEANUP =================
    def cog_unload(self):
        self.temp_channels.clear()


async def setup(bot):
    await bot.add_cog(JoinToCreate(bot))
