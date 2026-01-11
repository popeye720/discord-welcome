import discord
from discord.ext import commands
from discord import app_commands
from database.models import jtc_col


class JoinToCreate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.temp_channels = {}  # vc_id : creator_id
        self._ready_done = False

    # ---------------- PERMISSION CHECK ----------------
    async def can_manage(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ---------------- BOT READY ----------------
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

    # ---------------- CREATE JTC ----------------
    @app_commands.command(name="createjtc", description="Create a Join-to-Create voice channel")
    async def create_jtc(self, interaction: discord.Interaction, category_id: int):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )

        existing = jtc_col.find_one({"guild_id": interaction.guild.id})
        if existing:
            return await interaction.response.send_message(
                "❌ Join-to-Create is already set up for this server.",
                ephemeral=True
            )

        category = interaction.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Invalid category ID.", ephemeral=True
            )

        channel = await interaction.guild.create_voice_channel(
            name="Join to Create",
            category=category
        )

        jtc_col.insert_one({
            "guild_id": interaction.guild.id,
            "category_id": category.id,
            "jtc_channel_id": channel.id
        })

        await interaction.response.send_message(
            f"✅ Join-to-Create created in category **{category.name}**",
            ephemeral=True
        )

    # ---------------- DELETE JTC ----------------
    @app_commands.command(name="deletejtc", description="Delete the Join-to-Create channel")
    async def delete_jtc(self, interaction: discord.Interaction):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )

        conf = jtc_col.find_one({"guild_id": interaction.guild.id})
        if not conf:
            return await interaction.response.send_message(
                "❌ Join-to-Create is not configured in this server.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(conf.get("jtc_channel_id"))
        if isinstance(channel, discord.VoiceChannel):
            try:
                await channel.delete()
            except Exception:
                pass

        jtc_col.delete_one({"guild_id": interaction.guild.id})
        await interaction.response.send_message(
            "✅ Join-to-Create system has been disabled.", ephemeral=True
        )

    # ---------------- VC ALLOW ----------------
    @app_commands.command(name="vcallow", description="Allow a member in your temporary VC")
    async def vc_allow(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "You must be inside your voice channel.", ephemeral=True
            )

        vc = interaction.user.voice.channel
        creator_id = self.temp_channels.get(vc.id)

        if interaction.user.id != creator_id and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                "You do not have permission to manage this voice channel.", ephemeral=True
            )

        if member.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "Server owner already has full access.", ephemeral=True
            )

        await vc.set_permissions(member, connect=True, speak=True)
        await interaction.response.send_message(f"{member.mention} is now allowed.", ephemeral=True)

    # ---------------- VC REMOVE ----------------
    @app_commands.command(name="vcremove", description="Remove a member from your temporary VC")
    async def vc_remove(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "You must be inside your voice channel.", ephemeral=True
            )

        vc = interaction.user.voice.channel
        creator_id = self.temp_channels.get(vc.id)

        if interaction.user.id != creator_id and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                "You do not have permission to manage this voice channel.", ephemeral=True
            )

        if member.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "Server owner cannot be removed.", ephemeral=True
            )

        if member in vc.members:
            try:
                await member.move_to(None)
            except Exception:
                pass

        await vc.set_permissions(member, connect=False)
        await interaction.response.send_message(f"{member.mention} has been removed.", ephemeral=True)

    # ---------------- VOICE LISTENER ----------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conf = jtc_col.find_one({"guild_id": member.guild.id})
        if not conf:
            return

        jtc_id = conf.get("jtc_channel_id")

        # -------- JOINED JTC --------
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

        # -------- CREATOR LEFT --------
        if before.channel and before.channel.id in self.temp_channels:
            vc = before.channel
            creator_id = self.temp_channels.get(vc.id)
            owner = vc.guild.owner

            creator = vc.guild.get_member(creator_id)
            if creator and creator in vc.members:
                return

            if owner and owner in vc.members:
                return

            for m in vc.members:
                try:
                    await m.move_to(None)
                except Exception:
                    pass

            try:
                await vc.delete()
            except Exception:
                pass

            self.temp_channels.pop(vc.id, None)

    # ---------------- CLEANUP ----------------
    def cog_unload(self):
        self.temp_channels.clear()

    # ---------------- GLOBAL CHECK ----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.can_manage(interaction)


# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreate(bot))
