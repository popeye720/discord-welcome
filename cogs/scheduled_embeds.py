import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import re
import uuid

from database.models import scheduled_embeds_col

# ✅ IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


# ================= MODAL (MESSAGE INPUT) =================
class EmbedModal(discord.ui.Modal):
    """
    Re-usable modal that returns:
    - message text
    - optional image attachment
    - optional mention role/user (ids)
    - optional ping_everyone fallback
    """
    def __init__(
        self,
        title: str,
        callback,
        image: discord.Attachment | None = None,
        mention_role: discord.Role | None = None,
        mention_user: discord.User | None = None,
        ping_everyone: bool = False,
    ):
        super().__init__(title=title)
        self._callback = callback
        self._image = image
        self._mention_role = mention_role
        self._mention_user = mention_user
        self._ping_everyone = ping_everyone

        self.message = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
            placeholder="Type your message here..."
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(
            interaction,
            self.message.value,
            self._image,
            self._mention_role,
            self._mention_user,
            self._ping_everyone
        )


class ScheduledEmbedsSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================= LIFECYCLE =================
    async def cog_load(self):
        if not self.scheduler.is_running():
            self.scheduler.start()
        print("✅ ScheduledEmbedsSlash cog loaded (scheduler started)")

    async def cog_unload(self):
        if self.scheduler.is_running():
            self.scheduler.cancel()
        print("❌ ScheduledEmbedsSlash cog unloaded (scheduler stopped)")

    # ================= PERMISSION =================
    def can_manage(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.guild is not None
            and (
                interaction.user.id == interaction.guild.owner_id
                or interaction.user.guild_permissions.administrator
            )
        )

    # ================= HELPERS =================
    def _strip_seconds(self, dt: datetime) -> datetime:
        return dt.replace(second=0, microsecond=0)

    def to_utc(self, dt_ist: datetime) -> datetime:
        """IST aware -> UTC aware"""
        return dt_ist.astimezone(timezone.utc)

    def to_ist(self, dt_utc: datetime) -> datetime:
        """UTC aware -> IST aware"""
        return dt_utc.astimezone(IST)

    def _is_image_attachment(self, att: discord.Attachment | None) -> bool:
        if not att:
            return False
        if att.content_type and att.content_type.startswith("image"):
            return True
        # fallback if content_type missing
        fn = (att.filename or "").lower()
        return fn.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))

    def _build_confirmation_embed(
        self,
        *,
        schedule_id: str,
        channel: discord.TextChannel,
        send_time_utc: datetime,
        send_time_ist: datetime,
        mention_role: discord.Role | None,
        mention_user: discord.User | None,
        ping_everyone: bool,
        image: discord.Attachment | None
    ) -> discord.Embed:
        embed = discord.Embed(
            title="✅ Scheduled embed created",
            color=discord.Color.gold()
        )

        embed.add_field(name="ID", value=f"`{schedule_id}`", inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)

        embed.add_field(
            name="Time (IST)",
            value=f"`{send_time_ist.strftime('%Y-%m-%d %H:%M')}`",
            inline=False
        )
        embed.add_field(
            name="Time (UTC)",
            value=f"`{send_time_utc.strftime('%Y-%m-%d %H:%M')}`",
            inline=False
        )

        mention_lines = []
        if mention_role:
            mention_lines.append(f"Role: {mention_role.mention}")
        if mention_user:
            mention_lines.append(f"User: {mention_user.mention}")
        if ping_everyone:
            mention_lines.append("@everyone: `yes`")

        embed.add_field(
            name="Mentions",
            value="\n".join(mention_lines) if mention_lines else "`none`",
            inline=False
        )

        # ✅ Optional image: thumbnail + big image
        if self._is_image_attachment(image):
            embed.set_thumbnail(url=image.url)
            embed.set_image(url=image.url)

        return embed

    def _build_send_content_and_mentions(
        self,
        *,
        mention_role_id: int | None,
        mention_user_id: int | None,
        ping_everyone: bool
    ):
        parts = []

        # Prefer role/user mention (as you asked)
        if mention_role_id:
            parts.append(f"<@&{mention_role_id}>")
        if mention_user_id:
            parts.append(f"<@{mention_user_id}>")

        # Fallback to everyone if no role mention and requested
        if ping_everyone and not mention_role_id:
            parts.append("@everyone")

        content = " ".join(parts) if parts else None

        allowed = discord.AllowedMentions(
            everyone=bool(ping_everyone and not mention_role_id),
            roles=bool(mention_role_id),
            users=bool(mention_user_id),
            replied_user=False
        )
        return content, allowed

    # ================= TIME PARSER (IST INPUT) =================
    def parse_time(self, time_str: str):
        time_str = time_str.strip()

        # supports: 10m / 2h / 1d  (✅ IST now)
        if re.match(r"^\d+[mhd]$", time_str):
            value = int(time_str[:-1])
            unit = time_str[-1]

            now_ist = datetime.now(IST)
            if unit == "m":
                dt_ist = now_ist + timedelta(minutes=value)
            elif unit == "h":
                dt_ist = now_ist + timedelta(hours=value)
            else:  # "d"
                dt_ist = now_ist + timedelta(days=value)

            dt_ist = self._strip_seconds(dt_ist)
            return self.to_utc(dt_ist)  # ✅ store UTC

        # supports: "YYYY-MM-DD HH:MM"  (✅ treat as IST)
        try:
            naive = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            dt_ist = naive.replace(tzinfo=IST)
            dt_ist = self._strip_seconds(dt_ist)
            return self.to_utc(dt_ist)  # ✅ store UTC
        except ValueError:
            return None

    # =========================================================
    # ✅ GROUP: /schedule
    # =========================================================
    schedule = app_commands.Group(
        name="schedule",
        description="Schedule embed messages (IST input, stored in UTC)"
    )

    # ================= /schedule create (MODAL) =================
    @schedule.command(name="create", description="Create a scheduled embed")
    @app_commands.describe(
        channel="Target channel",
        time="Time: 10m / 2h / 1d OR 'YYYY-MM-DD HH:MM' (IST)",
        image="Optional image (thumbnail + big image)",
        mention_role="Optional role to mention (preferred over @everyone)",
        mention_user="Optional user to mention",
        ping_everyone="Fallback ping @everyone (only used if no role mention)"
    )
    async def schedule_create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        time: str,
        image: discord.Attachment | None = None,
        mention_role: discord.Role | None = None,
        mention_user: discord.User | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        send_time_utc = self.parse_time(time)
        if not send_time_utc:
            return await interaction.response.send_message(
                "❌ Invalid time format.\nUse: `10m / 2h / 1d` OR `YYYY-MM-DD HH:MM` (IST).",
                ephemeral=True
            )

        # Permission checks:
        # - @everyone requires mention_everyone permission (same as before)
        # - role mention doesn't require mention_everyone, but still controlled by AllowedMentions
        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.",
                ephemeral=True
            )

        async def create_schedule(
            i: discord.Interaction,
            message: str,
            modal_image: discord.Attachment | None,
            modal_role: discord.Role | None,
            modal_user: discord.User | None,
            modal_ping_everyone: bool
        ):
            msg2 = message.strip()

            # backward compatible: allow "--ping" typed inside modal (only if no role mention)
            ping2 = bool(modal_ping_everyone)
            if msg2.startswith("--ping"):
                if not i.user.guild_permissions.mention_everyone:
                    return await i.response.send_message("❌ You cannot ping @everyone.", ephemeral=True)
                ping2 = True
                msg2 = msg2.replace("--ping", "", 1).strip()

            schedule_id = uuid.uuid4().hex[:8]

            image_url = None
            if self._is_image_attachment(modal_image):
                image_url = modal_image.url

            scheduled_embeds_col.insert_one({
                "guild_id": i.guild.id,
                "schedule_id": schedule_id,
                "channel_id": channel.id,
                "send_time": send_time_utc,  # ✅ UTC stored
                "message": msg2,

                # ✅ new mention system
                "mention_role_id": modal_role.id if modal_role else None,
                "mention_user_id": modal_user.id if modal_user else None,

                # ✅ fallback (kept for core-logic compatibility)
                "ping_everyone": bool(ping2),

                # ✅ optional image
                "image_url": image_url,

                "author_id": i.user.id
            })

            send_time_ist = self.to_ist(send_time_utc)

            confirm_embed = self._build_confirmation_embed(
                schedule_id=schedule_id,
                channel=channel,
                send_time_utc=send_time_utc,
                send_time_ist=send_time_ist,
                mention_role=modal_role,
                mention_user=modal_user,
                ping_everyone=bool(ping2 and not (modal_role is not None)),  # show true only if it will be used
                image=modal_image
            )

            await i.response.send_message(embed=confirm_embed, ephemeral=True)

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Schedule Embed → #{channel.name}",
                callback=create_schedule,
                image=image,
                mention_role=mention_role,
                mention_user=mention_user,
                ping_everyone=ping_everyone
            )
        )

    # ================= /schedule list =================
    @schedule.command(name="list", description="List scheduled embeds (shows IST + UTC)")
    async def schedule_list(self, interaction: discord.Interaction):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        data = list(scheduled_embeds_col.find({"guild_id": interaction.guild.id}))
        if not data:
            return await interaction.response.send_message("📭 No scheduled embeds.", ephemeral=True)

        # Sort by UTC time
        try:
            data.sort(key=lambda x: x.get("send_time", datetime.max.replace(tzinfo=timezone.utc)))
        except Exception:
            pass

        desc_lines = []
        for d in data[:25]:
            dt_utc = d["send_time"]
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            dt_ist = self.to_ist(dt_utc)

            role_id = d.get("mention_role_id")
            user_id = d.get("mention_user_id")
            ping_everyone = bool(d.get("ping_everyone") or d.get("ping"))  # support old docs
            image_url = d.get("image_url")

            mention_parts = []
            if role_id:
                mention_parts.append(f"<@&{role_id}>")
            if user_id:
                mention_parts.append(f"<@{user_id}>")
            if ping_everyone and not role_id:
                mention_parts.append("@everyone")

            desc_lines.append(
                f"**ID:** `{d['schedule_id']}`\n"
                f"Channel: <#{d['channel_id']}>\n"
                f"IST: `{dt_ist.strftime('%Y-%m-%d %H:%M')}`\n"
                f"UTC: `{dt_utc.strftime('%Y-%m-%d %H:%M')}`\n"
                f"Mentions: {(' '.join(mention_parts) if mention_parts else '`none`')}\n"
                f"Image: `{'yes' if image_url else 'no'}`\n"
            )

        if len(data) > 25:
            desc_lines.append(f"…and **{len(data) - 25}** more.")

        embed = discord.Embed(
            title="📅 Scheduled Embeds",
            description="\n".join(desc_lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= /schedule delete =================
    @schedule.command(name="delete", description="Delete a scheduled embed by its ID")
    @app_commands.describe(schedule_id="Schedule ID (8 chars)")
    async def schedule_delete(self, interaction: discord.Interaction, schedule_id: str):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        result = scheduled_embeds_col.find_one_and_delete({
            "guild_id": interaction.guild.id,
            "schedule_id": schedule_id
        })

        if not result:
            return await interaction.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

        embed = discord.Embed(
            title="🗑️ Scheduled embed deleted",
            description=f"ID: `{schedule_id}`",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= /schedule edit (MODAL) =================
    @schedule.command(name="edit", description="Edit the message/mentions/image of a scheduled embed (uses modal)")
    @app_commands.describe(
        schedule_id="Schedule ID (8 chars)",
        image="Optional new image",
        mention_role="Optional role to mention",
        mention_user="Optional user to mention",
        ping_everyone="Fallback ping @everyone (only used if no role mention)"
    )
    async def schedule_edit(
        self,
        interaction: discord.Interaction,
        schedule_id: str,
        image: discord.Attachment | None = None,
        mention_role: discord.Role | None = None,
        mention_user: discord.User | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        existing = scheduled_embeds_col.find_one({
            "guild_id": interaction.guild.id,
            "schedule_id": schedule_id
        })
        if not existing:
            return await interaction.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.",
                ephemeral=True
            )

        async def edit_schedule(
            i: discord.Interaction,
            new_message: str,
            modal_image: discord.Attachment | None,
            modal_role: discord.Role | None,
            modal_user: discord.User | None,
            modal_ping_everyone: bool
        ):
            msg2 = new_message.strip()

            ping2 = bool(modal_ping_everyone)
            if msg2.startswith("--ping"):
                if not i.user.guild_permissions.mention_everyone:
                    return await i.response.send_message("❌ You cannot ping @everyone.", ephemeral=True)
                ping2 = True
                msg2 = msg2.replace("--ping", "", 1).strip()

            set_doc = {
                "message": msg2,
                "mention_role_id": modal_role.id if modal_role else None,
                "mention_user_id": modal_user.id if modal_user else None,
                "ping_everyone": bool(ping2),
            }

            if self._is_image_attachment(modal_image):
                set_doc["image_url"] = modal_image.url
            elif modal_image is None:
                # if user didn't provide image param, keep old image_url
                pass
            else:
                # provided but not image -> remove
                set_doc["image_url"] = None

            updated = scheduled_embeds_col.find_one_and_update(
                {"guild_id": i.guild.id, "schedule_id": schedule_id},
                {"$set": set_doc}
            )

            if not updated:
                return await i.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

            embed = discord.Embed(
                title="✏️ Scheduled embed updated",
                description=f"ID: `{schedule_id}`",
                color=discord.Color.gold()
            )
            await i.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Edit Scheduled Embed → {schedule_id}",
                callback=edit_schedule,
                image=image,
                mention_role=mention_role,
                mention_user=mention_user,
                ping_everyone=ping_everyone
            )
        )

    # ================= /schedule time =================
    @schedule.command(name="time", description="Change the send time of a scheduled embed (IST input)")
    @app_commands.describe(
        schedule_id="Schedule ID (8 chars)",
        new_time="Time: 10m / 2h / 1d OR 'YYYY-MM-DD HH:MM' (IST)"
    )
    async def schedule_time(self, interaction: discord.Interaction, schedule_id: str, new_time: str):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        new_dt_utc = self.parse_time(new_time)
        if not new_dt_utc:
            return await interaction.response.send_message(
                "❌ Invalid time format.\nUse: `10m / 2h / 1d` OR `YYYY-MM-DD HH:MM` (IST).",
                ephemeral=True
            )

        result = scheduled_embeds_col.find_one_and_update(
            {"guild_id": interaction.guild.id, "schedule_id": schedule_id},
            {"$set": {"send_time": new_dt_utc}}
        )

        if not result:
            return await interaction.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

        embed = discord.Embed(
            title="⏰ Schedule time updated",
            description=(
                f"ID: `{schedule_id}`\n"
                f"New time (IST): `{new_dt_utc.astimezone(IST).strftime('%Y-%m-%d %H:%M')}`\n"
                f"New time (UTC): `{new_dt_utc.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')}`"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= RUNNER (COMPARE IN UTC) =================
    @tasks.loop(seconds=20)
    async def scheduler(self):
        now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        data = list(scheduled_embeds_col.find({
            "send_time": {"$lte": now_utc}
        }))

        for d in data:
            channel = self.bot.get_channel(d["channel_id"])
            if not channel:
                scheduled_embeds_col.delete_one({"_id": d["_id"]})
                continue

            embed = discord.Embed(
                description=d.get("message", ""),
                color=discord.Color.gold()
            )

            # optional image
            image_url = d.get("image_url")
            if image_url:
                embed.set_thumbnail(url=image_url)
                embed.set_image(url=image_url)

            # mentions (new + old compatibility)
            mention_role_id = d.get("mention_role_id")
            mention_user_id = d.get("mention_user_id")

            ping_everyone = bool(d.get("ping_everyone"))
            if "ping_everyone" not in d:
                # old docs used "ping"
                ping_everyone = bool(d.get("ping"))

            content, allowed = self._build_send_content_and_mentions(
                mention_role_id=mention_role_id,
                mention_user_id=mention_user_id,
                ping_everyone=ping_everyone
            )

            try:
                await channel.send(
                    content=content,
                    embed=embed,
                    allowed_mentions=allowed
                )
            except Exception as e:
                print("❌ Failed to send scheduled embed:", e)

            scheduled_embeds_col.delete_one({"_id": d["_id"]})

    @scheduler.before_loop
    async def before_scheduler(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduledEmbedsSlash(bot))
