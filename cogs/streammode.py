import discord
from discord.ext import commands
from discord import app_commands
from database.models import streammode_col
import datetime

class StreamMode(commands.Cog):
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

    # ----------------- /stream-mode -----------------
    @app_commands.command(
        name="stream-mode",
        description="Enable stream mode (blocks bots from joining your current VC)"
    )
    @app_commands.guild_only()
    async def streammode(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            # silent ignore (as you wanted earlier)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be connected to a voice channel.",
                ephemeral=True
            )

        vc = interaction.user.voice.channel

        if streammode_col.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "⚠️ Stream mode is already ENABLED.",
                ephemeral=True
            )

        streammode_col.insert_one({
            "guild_id": interaction.guild.id,
            "vc_id": vc.id,
            "enabled": True
        })

        await interaction.response.send_message(
            f"✅ **Stream Mode Enabled**\n"
            f"🔒 Bots are blocked from **{vc.name}**",
            ephemeral=True
        )

    # ----------------- /stream-mode-off -----------------
    @app_commands.command(
        name="stream-mode-off",
        description="Disable stream mode"
    )
    @app_commands.guild_only()
    async def streammodeoff(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        result = streammode_col.delete_one({"guild_id": interaction.guild.id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "⚠️ Stream mode is already OFF.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🟢 **Stream Mode Disabled**",
            ephemeral=True
        )

    # ----------------- /status-stream -----------------
    @app_commands.command(
        name="status-stream",
        description="Check stream mode status"
    )
    @app_commands.guild_only()
    async def statusstream(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        data = streammode_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return await interaction.response.send_message(
                "🔴 **Stream Mode:** OFF",
                ephemeral=True
            )

        vc = interaction.guild.get_channel(data["vc_id"])
        await interaction.response.send_message(
            f"🟢 **Stream Mode:** ON\n"
            f"🔒 VC: **{vc.name if vc else 'Unknown'}**",
            ephemeral=True
        )

    # ----------------- HELPER: FIND WHO MOVED THE BOT (AUDIT LOG) -----------------
    async def _find_mover_from_audit_logs(
        self,
        guild: discord.Guild,
        target_member: discord.Member
    ) -> discord.Member | None:
        """
        Tries to find who moved the member using audit logs.
        Needs 'View Audit Log' permission.
        """
        try:
            me = guild.me or guild.get_member(self.bot.user.id)
            if not me or not me.guild_permissions.view_audit_log:
                return None

            # check latest entries
            async for entry in guild.audit_logs(limit=6, action=discord.AuditLogAction.member_move):
                # entry.target can be Member/User depending on cache
                if entry.target and getattr(entry.target, "id", None) == target_member.id:
                    # time window check (last ~10 seconds)
                    created = entry.created_at.replace(tzinfo=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - created).total_seconds() <= 10:
                        return entry.user  # the moderator who moved
        except Exception:
            pass
        return None

    # ----------------- HELPER: DM USER -----------------
    async def _dm_user(self, user: discord.abc.User, message: str) -> bool:
        try:
            await user.send(message)
            return True
        except discord.Forbidden:
            return False
        except Exception:
            return False

    # ----------------- BLOCK BOTS + USER NOTICE (DM) -----------------
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        # only bots
        if not member.guild or not member.bot:
            return

        data = streammode_col.find_one({"guild_id": member.guild.id})
        if not data or not data.get("enabled"):
            return

        blocked_vc_id = data["vc_id"]

        # bot joined the blocked VC
        if after.channel and after.channel.id == blocked_vc_id:
            guild = member.guild
            vc = after.channel

            # 1) Kick the bot out
            try:
                await member.move_to(None)
            except Exception:
                pass

            # 2) Find who moved it (best effort)
            mover = await self._find_mover_from_audit_logs(guild, member)

            # fallback heuristic (if audit log not available)
            if mover is None:
                for m in vc.members:
                    if not m.bot and m.guild_permissions.move_members:
                        mover = m
                        break

            # 3) DM the mover (only that user sees)
            if mover:
                dm_ok = await self._dm_user(
                    mover,
                    f"🚫 **Stream Mode is enabled in VC: {vc.name}**\n"
                    f"🤖 Bots are not allowed there, so I removed **{member.name}** from the channel."
                )

                # optional fallback: if DM closed, send short msg in VC text chat (if exists)
                if not dm_ok:
                    try:
                        await vc.send(
                            f"🚫 {mover.mention} Stream Mode is enabled here. Bots are not allowed.",
                            delete_after=5
                        )
                    except Exception:
                        pass

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamMode(bot))
