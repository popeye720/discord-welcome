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
    def __init__(self, title: str, callback, ping_everyone: bool = False):
        super().__init__(title=title)
        self._callback = callback
        self._ping = ping_everyone

        self.message = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
            placeholder="Type your message here..."
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(interaction, self.message.value, self._ping)


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
        ping_everyone="Ping @everyone?"
    )
    async def schedule_create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        time: str,
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

        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.",
                ephemeral=True
            )

        async def create_schedule(i: discord.Interaction, message: str, ping: bool):
            ping2 = ping
            msg2 = message.strip()

            # (backward compatible) allow "--ping" typed inside modal too
            if msg2.startswith("--ping"):
                if not i.user.guild_permissions.mention_everyone:
                    return await i.response.send_message("❌ You cannot ping @everyone.", ephemeral=True)
                ping2 = True
                msg2 = msg2.replace("--ping", "", 1).strip()

            schedule_id = uuid.uuid4().hex[:8]
            scheduled_embeds_col.insert_one({
                "guild_id": i.guild.id,
                "schedule_id": schedule_id,
                "channel_id": channel.id,
                "send_time": send_time_utc,  # ✅ UTC stored
                "message": msg2,
                "ping": ping2,
                "author_id": i.user.id
            })

            send_time_ist = self.to_ist(send_time_utc)

            await i.response.send_message(
                "✅ Scheduled embed created\n"
                f"🆔 ID: `{schedule_id}`\n"
                f"📍 Channel: {channel.mention}\n"
                f"🇮🇳 Time (IST): `{send_time_ist.strftime('%Y-%m-%d %H:%M')}`\n"
                f"🌍 Time (UTC): `{send_time_utc.strftime('%Y-%m-%d %H:%M')}`",
                ephemeral=True
            )

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Schedule Embed → #{channel.name}",
                callback=create_schedule,
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

            desc_lines.append(
                f"**ID:** `{d['schedule_id']}`\n"
                f"Channel: <#{d['channel_id']}>\n"
                f"IST: `{dt_ist.strftime('%Y-%m-%d %H:%M')}`\n"
                f"UTC: `{dt_utc.strftime('%Y-%m-%d %H:%M')}`\n"
                f"Ping: `{'yes' if d.get('ping') else 'no'}`\n"
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

        await interaction.response.send_message(f"🗑️ Schedule `{schedule_id}` deleted.", ephemeral=True)

    # ================= /schedule edit (MODAL) =================
    @schedule.command(name="edit", description="Edit the message of a scheduled embed (uses modal)")
    @app_commands.describe(
        schedule_id="Schedule ID (8 chars)",
        ping_everyone="Ping @everyone?"
    )
    async def schedule_edit(
        self,
        interaction: discord.Interaction,
        schedule_id: str,
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

        async def edit_schedule(i: discord.Interaction, new_message: str, ping: bool):
            ping2 = ping
            msg2 = new_message.strip()

            if msg2.startswith("--ping"):
                if not i.user.guild_permissions.mention_everyone:
                    return await i.response.send_message("❌ You cannot ping @everyone.", ephemeral=True)
                ping2 = True
                msg2 = msg2.replace("--ping", "", 1).strip()

            updated = scheduled_embeds_col.find_one_and_update(
                {"guild_id": i.guild.id, "schedule_id": schedule_id},
                {"$set": {"message": msg2, "ping": ping2}}
            )

            if not updated:
                return await i.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

            await i.response.send_message(f"✏️ Schedule `{schedule_id}` updated.", ephemeral=True)

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Edit Scheduled Embed → {schedule_id}",
                callback=edit_schedule,
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

        await interaction.response.send_message(
            f"⏰ Schedule `{schedule_id}` rescheduled to "
            f"`{new_dt_utc.astimezone(IST).strftime('%Y-%m-%d %H:%M')}` (IST).",
            ephemeral=True
        )

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
                description=d["message"],
                color=discord.Color.gold()
            )

            try:
                await channel.send(
                    content="@everyone" if d.get("ping") else None,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(everyone=bool(d.get("ping")))
                )
            except Exception as e:
                print("❌ Failed to send scheduled embed:", e)

            scheduled_embeds_col.delete_one({"_id": d["_id"]})

    @scheduler.before_loop
    async def before_scheduler(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduledEmbedsSlash(bot))
