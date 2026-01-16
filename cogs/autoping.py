import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from database.mongo import db
from database.models import autoping_rules



class AutoPing(commands.Cog):
    """
    DB-based auto ping trigger:
    - Admin/Owner sets a rule for a target user
    - Whenever target sends ANY message in ANY guild channel,
      bot posts ping + optional text + optional photo/video link
    - Stops after N times (remaining hits).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- CENTRALIZED PERMISSION (OWNER / ADMIN) -----------------
    def can_manage(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        perms = getattr(interaction.user, "guild_permissions", None)
        return bool(perms and perms.administrator)

    async def deny_silent(self, interaction: discord.Interaction) -> bool:
        # streammode style: no leak, just ephemeral
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Admin/Owner only.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Admin/Owner only.", ephemeral=True)
        except:
            pass
        return False

    # ----------------- COMMAND GROUP -----------------
    autoping = app_commands.Group(
        name="autoping",
        description="Auto ping a specific user when they type (Admin/Owner only)."
    )

    # Hide from normal users (Discord permission-gated UI)
    # NOTE: Owner usually has all perms; check still enforces owner/admin.
    @autoping.command(name="set", description="Set auto ping rule for a user (Admin/Owner only).")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def autoping_set(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        times: app_commands.Range[int, 1, 100] = 5,
        text: str | None = None,
        photo: discord.Attachment | None = None,
        video: discord.Attachment | None = None,
    ):
        if not self.can_manage(interaction):
            return await self.deny_silent(interaction)

        guild = interaction.guild
        assert guild is not None

        photo_url = photo.url if photo else None
        video_url = video.url if video else None

        doc = {
            "guild_id": guild.id,
            "target_user_id": user.id,
            "text": text or None,
            "photo_url": photo_url,
            "video_url": video_url,
            "total": int(times),
            "remaining": int(times),
            "set_by": interaction.user.id,
            "set_at": datetime.utcnow().isoformat()
        }

        autoping_col.update_one(
            {"guild_id": guild.id, "target_user_id": user.id},
            {"$set": doc},
            upsert=True
        )

        # Confirm (ephemeral)
        lines = [
            "✅ AutoPing rule set.",
            f"Target: {user.mention}",
            f"Times: {times}",
            f"Text: {'(none)' if not text else text[:200]}",
            f"Photo: {'(none)' if not photo_url else photo_url}",
            f"Video: {'(none)' if not video_url else video_url}",
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @autoping.command(name="remove", description="Remove auto ping rule for a user (Admin/Owner only).")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def autoping_remove(self, interaction: discord.Interaction, user: discord.Member):
        if not self.can_manage(interaction):
            return await self.deny_silent(interaction)

        guild = interaction.guild
        assert guild is not None

        res = autoping_col.delete_one({"guild_id": guild.id, "target_user_id": user.id})
        if res.deleted_count:
            return await interaction.response.send_message(f"🗑️ Removed rule for {user.mention}", ephemeral=True)
        return await interaction.response.send_message(f"⚠️ No rule found for {user.mention}", ephemeral=True)

    @autoping.command(name="view", description="View auto ping rule for a user (Admin/Owner only).")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def autoping_view(self, interaction: discord.Interaction, user: discord.Member):
        if not self.can_manage(interaction):
            return await self.deny_silent(interaction)

        guild = interaction.guild
        assert guild is not None

        data = autoping_col.find_one({"guild_id": guild.id, "target_user_id": user.id})
        if not data:
            return await interaction.response.send_message(f"⚠️ No rule found for {user.mention}", ephemeral=True)

        await interaction.response.send_message(
            "\n".join([
                "📌 AutoPing rule:",
                f"Target: {user.mention}",
                f"Remaining: {data.get('remaining', 0)}/{data.get('total', 0)}",
                f"Text: {'(none)' if not data.get('text') else data.get('text')[:300]}",
                f"Photo: {'(none)' if not data.get('photo_url') else data.get('photo_url')}",
                f"Video: {'(none)' if not data.get('video_url') else data.get('video_url')}",
            ]),
            ephemeral=True
        )

    # ----------------- MESSAGE LISTENER -----------------
    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        # Ignore bots, DMs, system
        if not message.guild or message.author.bot:
            return

        # Fast lookup rule
        data = autoping_col.find_one(
            {"guild_id": message.guild.id, "target_user_id": message.author.id},
            {"text": 1, "photo_url": 1, "video_url": 1, "remaining": 1, "total": 1}
        )
        if not data:
            return

        remaining = int(data.get("remaining", 0))
        if remaining <= 0:
            # optional cleanup
            try:
                autoping_col.delete_one({"guild_id": message.guild.id, "target_user_id": message.author.id})
            except:
                pass
            return

        # Build outgoing message
        parts = [message.author.mention]  # Ping ONLY target user (same as message author)
        text = data.get("text")
        if text:
            parts.append(text)

        photo_url = data.get("photo_url")
        video_url = data.get("video_url")

        # Send links so Discord auto-embeds (works for photo/video)
        if photo_url:
            parts.append(photo_url)
        if video_url:
            parts.append(video_url)

        out = "\n".join(parts).strip()

        try:
            await message.channel.send(out)
        except:
            return

        # Decrement remaining
        new_remaining = remaining - 1
        try:
            if new_remaining <= 0:
                autoping_col.delete_one({"guild_id": message.guild.id, "target_user_id": message.author.id})
            else:
                autoping_col.update_one(
                    {"guild_id": message.guild.id, "target_user_id": message.author.id},
                    {"$set": {"remaining": new_remaining}}
                )
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoPing(bot))