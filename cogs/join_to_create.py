import discord
from discord.ext import commands
from database.models import jtc_col


class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}   # vc_id : creator_id
        self._ready_done = False

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

        old_channel = guild.get_channel(conf.get("jtc_channel_id"))
        if isinstance(old_channel, discord.VoiceChannel):
            try:
                await old_channel.delete()
            except Exception:
                pass

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
            return await ctx.reply("You do not have permission to use this command.")

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.reply("Invalid category ID.")

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
            return await ctx.reply("You do not have permission to use this command.")

        conf = jtc_col.find_one({"guild_id": ctx.guild.id})
        if not conf:
            return await ctx.reply("Join-to-Create is not configured for this server.")

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
        await ctx.reply("Join-to-Create system has been disabled successfully.")

    # ================= VC ALLOW =================
    @commands.command(name="vcallow")
    async def vc_allow(self, ctx, member: discord.Member):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("You must be inside your voice channel.")

        vc = ctx.author.voice.channel
        creator_id = self.temp_channels.get(vc.id)

        if ctx.author.id != creator_id and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("You do not have permission to manage this voice channel.")

        # Owner already has full access by default
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("The server owner already has full access to this voice channel.")

        await vc.set_permissions(
            member,
            connect=True,
            speak=True
        )

        await ctx.reply(f"{member.mention} has been allowed to join the voice channel.")

    # ================= VC REMOVE =================
    @commands.command(name="vcremove")
    async def vc_remove(self, ctx, member: discord.Member):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("You must be inside your voice channel.")

        vc = ctx.author.voice.channel
        creator_id = self.temp_channels.get(vc.id)

        if ctx.author.id != creator_id and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("You do not have permission to manage this voice channel.")

        # Owner protection (cannot be removed)
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("The server owner cannot be removed from a voice channel.")

        if member in vc.members:
            try:
                await member.move_to(None)
            except Exception:
                pass

        await vc.set_permissions(
            member,
            connect=False
        )

        await ctx.reply(f"{member.mention} has been removed from the voice channel.")

    # ================= VOICE LISTENER =================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conf = jtc_col.find_one({"guild_id": member.guild.id})
        if not conf:
            return

        jtc_id = conf.get("jtc_channel_id")

        # -------- USER JOINED JTC --------
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

        # -------- CREATOR LEFT VC --------
        if before.channel and before.channel.id in self.temp_channels:
            vc = before.channel
            creator_id = self.temp_channels.get(vc.id)

            creator = vc.guild.get_member(creator_id)
            owner = vc.guild.owner

            if not creator or creator not in vc.members:
                if owner and owner in vc.members:
                    return

                for m in vc.members:
                    if owner and m.id == owner.id:
                        continue
                    try:
                        await m.move_to(None)
                    except Exception:
                        pass

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
