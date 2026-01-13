import discord
from discord.ext import commands
from discord import app_commands
from database.models import streammode_col
import datetime
from typing import Optional, List


class StreamMode(commands.Cog):
    """
    Stream Mode:
    - Admin/Owner can enable protection for ONE required VC, and optionally a SECOND VC.
    - If any bot joins any protected VC, it gets kicked from VC immediately.
    - No DMs to anyone.
    - Commands are silent for non-admin/owner (no leaks).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK (ADMIN / OWNER) -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # ----------------- /stream-mode (ENABLE) -----------------
    @app_commands.command(
        name="stream-mode",
        description="Enable stream mode (blocks bots from joining selected VC(s))"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        vc_1="Primary voice channel to protect (required)",
        vc_2="Optional second voice channel to protect"
    )
    async def streammode(
        self,
        interaction: discord.Interaction,
        vc_1: discord.VoiceChannel,
        vc_2: Optional[discord.VoiceChannel] = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        # Ensure channels belong to this guild (extra safety)
        if vc_1.guild.id != interaction.guild.id or (vc_2 and vc_2.guild.id != interaction.guild.id):
            return await interaction.response.send_message(
                "❌ Please select voice channels from this server only.",
                ephemeral=True
            )

        existing = streammode_col.find_one({"guild_id": interaction.guild.id})
        if existing and existing.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Stream mode is already **ENABLED**.",
                ephemeral=True
            )

        protected_vcs: List[int] = [vc_1.id]
        if vc_2 and vc_2.id != vc_1.id:
            protected_vcs.append(vc_2.id)

        # Upsert to keep it simple (enable + overwrite selected VCs)
        streammode_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": True, "vc_ids": protected_vcs}},
            upsert=True
        )

        desc = (
            f"🔒 **Bots are now blocked** from joining the selected voice channel(s).\n\n"
            f"🎙️ **VC 1:** {vc_1.mention}\n"
        )
        if vc_2 and vc_2.id != vc_1.id:
            desc += f"🎙️ **VC 2:** {vc_2.mention}\n"
        desc += f"🏠 **Server:** {interaction.guild.name}"

        embed = discord.Embed(
            title="✅ Stream Mode Enabled",
            description=desc,
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Stream Mode • Enabled")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- /stream-mode-off (DISABLE) -----------------
    @app_commands.command(
        name="stream-mode-off",
        description="Disable stream mode"
    )
    @app_commands.guild_only()
    async def streammodeoff(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        data = streammode_col.find_one({"guild_id": interaction.guild.id})
        if not data or not data.get("enabled"):
            return await interaction.response.send_message(
                "⚠️ Stream mode is already **OFF**.",
                ephemeral=True
            )

        # You can either delete the doc or just set enabled False.
        # Setting False keeps last selected VCs saved (optional nice behavior).
        streammode_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": False}}
        )

        embed = discord.Embed(
            title="🟢 Stream Mode Disabled",
            description=(
                f"Stream Mode has been turned **OFF**.\n\n"
                f"🏠 **Server:** {interaction.guild.name}"
            ),
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Stream Mode • Disabled")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- /status-stream (STATUS) -----------------
    @app_commands.command(
        name="status-stream",
        description="Check stream mode status"
    )
    @app_commands.guild_only()
    async def statusstream(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        data = streammode_col.find_one({"guild_id": interaction.guild.id})

        if not data or not data.get("enabled"):
            embed = discord.Embed(
                title="🔴 Stream Mode Status",
                description=(
                    f"Stream Mode is currently **OFF**.\n\n"
                    f"🏠 **Server:** {interaction.guild.name}"
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text="Stream Mode • Status")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        vc_ids = data.get("vc_ids") or []
        mentions = []
        for cid in vc_ids:
            ch = interaction.guild.get_channel(cid)
            mentions.append(ch.mention if ch else f"`Unknown ({cid})`")

        embed = discord.Embed(
            title="🟢 Stream Mode Status",
            description=(
                f"Stream Mode is currently **ON**.\n\n"
                f"🎙️ **Protected VC(s):** {', '.join(mentions) if mentions else 'None'}\n"
                f"🏠 **Server:** {interaction.guild.name}"
            ),
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Stream Mode • Status")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- BLOCK BOTS (NO DMs, NO AUDIT LOGS) -----------------
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        # only bots + only when they join/move into a channel
        if not member.guild or not member.bot or not after.channel:
            return

        data = streammode_col.find_one({"guild_id": member.guild.id})
        if not data or not data.get("enabled"):
            return

        protected_ids = data.get("vc_ids") or []
        if after.channel.id not in protected_ids:
            return

        # Kick bot from VC
        try:
            await member.move_to(None)
        except Exception:
            pass

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamMode(bot))