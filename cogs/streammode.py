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

    # ----------------- HELPER: DM USER (EMBED) -----------------
    # NOTE: We'll ONLY use this for the "mover" (the person who tried to move the bot).
    async def _dm_user(
        self,
        user: discord.abc.User,
        *,
        title: str,
        description: str,
        color: discord.Color = discord.Color.blurple(),
        footer: str | None = None
    ) -> bool:
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.datetime.utcnow()
            )
            if footer:
                embed.set_footer(text=footer)

            await user.send(embed=embed)
            return True
        except discord.Forbidden:
            return False
        except Exception:
            return False

    # ----------------- /stream-mode -----------------
    @app_commands.command(
        name="stream-mode",
        description="Enable stream mode (blocks bots from joining your current VC)"
    )
    @app_commands.guild_only()
    async def streammode(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be connected to a voice channel.",
                ephemeral=True
            )

        vc = interaction.user.voice.channel

        if streammode_col.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "⚠️ Stream mode is already **ENABLED**.",
                ephemeral=True
            )

        streammode_col.insert_one({
            "guild_id": interaction.guild.id,
            "vc_id": vc.id,
            "enabled": True
        })

        embed = discord.Embed(
            title="✅ Stream Mode Enabled",
            description=(
                f"🔒 **Bots are now blocked** from joining this voice channel.\n\n"
                f"🎙️ **VC:** {vc.mention}\n"
                f"🏠 **Server:** {interaction.guild.name}"
            ),
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Stream Mode • Enabled")

        # ✅ NO DM to the admin/owner — only ephemeral reply
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- /stream-mode-off -----------------
    @app_commands.command(
        name="stream-mode-off",
        description="Disable stream mode"
    )
    @app_commands.guild_only()
    async def streammodeoff(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        result = streammode_col.delete_one({"guild_id": interaction.guild.id})
        if result.deleted_count == 0:
            return await interaction.response.send_message(
                "⚠️ Stream mode is already **OFF**.",
                ephemeral=True
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

        # ✅ NO DM to the admin/owner — only ephemeral reply
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- /status-stream -----------------
    @app_commands.command(
        name="status-stream",
        description="Check stream mode status"
    )
    @app_commands.guild_only()
    async def statusstream(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        data = streammode_col.find_one({"guild_id": interaction.guild.id})

        if not data:
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

        vc = interaction.guild.get_channel(data["vc_id"])

        embed = discord.Embed(
            title="🟢 Stream Mode Status",
            description=(
                f"Stream Mode is currently **ON**.\n\n"
                f"🎙️ **VC:** {vc.mention if vc else 'Unknown'}\n"
                f"🏠 **Server:** {interaction.guild.name}"
            ),
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Stream Mode • Status")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- HELPER: FIND WHO MOVED THE BOT -----------------
    async def _find_mover_from_audit_logs(
        self,
        guild: discord.Guild,
        target_member: discord.Member
    ) -> discord.Member | None:
        try:
            me = guild.me or guild.get_member(self.bot.user.id)
            if not me or not me.guild_permissions.view_audit_log:
                return None

            async for entry in guild.audit_logs(
                limit=6,
                action=discord.AuditLogAction.member_move
            ):
                if entry.target and getattr(entry.target, "id", None) == target_member.id:
                    created = entry.created_at.replace(tzinfo=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - created).total_seconds() <= 10:
                        return entry.user
        except Exception:
            pass
        return None

    # ----------------- BLOCK BOTS + DM ONLY TO THE "MOVER" -----------------
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

        # bot tried to join the protected VC
        if after.channel and after.channel.id == data["vc_id"]:
            guild = member.guild
            vc = after.channel

            # kick bot from VC
            try:
                await member.move_to(None)
            except Exception:
                pass

            # find who moved the bot, then DM THAT PERSON only
            mover = await self._find_mover_from_audit_logs(guild, member)
            if mover:
                await self._dm_user(
                    mover,
                    title="🚫 Stream Mode Active",
                    description=(
                        f"Bots are **not allowed** in this voice channel.\n\n"
                        f"🤖 **Bot Removed:** {member.mention} (`{member.name}`)\n"
                        f"🎙️ **VC:** {vc.mention}"
                    ),
                    color=discord.Color.red(),
                    footer="Stream Mode Protection"
                )

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamMode(bot))
