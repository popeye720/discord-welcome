import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import re
import uuid

from database.models import scheduled_embeds_col


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

    # ================= TIME PARSER (SAME CORE LOGIC) =================
    def parse_time(self, time_str: str):
        # supports: 10m / 2h / 1d
        if re.match(r"^\d+[mhd]$", time_str):
            value = int(time_str[:-1])
            unit = time_str[-1]
            if unit == "m":
                return datetime.utcnow() + timedelta(minutes=value)
            if unit == "h":
                return datetime.utcnow() + timedelta(hours=value)
            if unit == "d":
                return datetime.utcnow() + timedelta(days=value)

        # supports: "YYYY-MM-DD HH:MM"
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return None

    # ================= /schembed CREATE (MODAL) =================
    @app_commands.command(
        name="schembed",
        description="Schedule an embed message in a channel (uses modal for message)"
    )
    @app_commands.describe(
        channel="Target channel",
        time="Time: 10m / 2h / 1d OR 'YYYY-MM-DD HH:MM' (UTC)",
        ping_everyone="Ping @everyone?"
    )
    async def schembed(
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

        send_time = self.parse_time(time)
        if not send_time:
            return await interaction.response.send_message(
                "❌ Invalid time format.\nUse: `10m / 2h / 1d` OR `YYYY-MM-DD HH:MM` (UTC).",
                ephemeral=True
            )

        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.",
                ephemeral=True
            )

        async def create_schedule(i: discord.Interaction, message: str, ping: bool):
            # (backward compatible) allow "--ping" typed inside modal too
            ping2 = ping
            msg2 = message.strip()
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
                "send_time": send_time,
                "message": msg2,
                "ping": ping2,
                "author_id": i.user.id
            })

            await i.response.send_message(
                "✅ Scheduled embed created\n"
                f"🆔 ID: `{schedule_id}`\n"
                f"📍 Channel: {channel.mention}\n"
                f"⏰ Time (UTC): `{send_time}`",
                ephemeral=True
            )

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Schedule Embed → #{channel.name}",
                callback=create_schedule,
                ping_everyone=ping_everyone
            )
        )

    # ================= /schembedlist LIST =================
    @app_commands.command(
        name="schembedlist",
        description="List all scheduled embeds in this server"
    )
    async def schembedlist(self, interaction: discord.Interaction):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        data = list(scheduled_embeds_col.find({"guild_id": interaction.guild.id}))
        if not data:
            return await interaction.response.send_message("📭 No scheduled embeds.", ephemeral=True)

        # Sort by time for nicer list
        try:
            data.sort(key=lambda x: x.get("send_time", datetime.max))
        except Exception:
            pass

        desc_lines = []
        for d in data[:25]:  # keep it safe for embed length
            desc_lines.append(
                f"**ID:** `{d['schedule_id']}`\n"
                f"Channel: <#{d['channel_id']}>\n"
                f"Time (UTC): `{d['send_time']}`\n"
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

    # ================= /schembeddelete DELETE =================
    @app_commands.command(
        name="schembeddelete",
        description="Delete a scheduled embed by its ID"
    )
    @app_commands.describe(schedule_id="Schedule ID (8 chars)")
    async def schembeddelete(self, interaction: discord.Interaction, schedule_id: str):
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

    # ================= /schembededit EDIT MESSAGE (MODAL) =================
    @app_commands.command(
        name="schembededit",
        description="Edit the message of a scheduled embed (uses modal)"
    )
    @app_commands.describe(
        schedule_id="Schedule ID (8 chars)",
        ping_everyone="Ping @everyone?"
    )
    async def schembededit(
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

            # (backward compatible) allow "--ping" typed inside modal too
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

    # ================= /schembedtime RESCHEDULE =================
    @app_commands.command(
        name="schembedtime",
        description="Change the send time of a scheduled embed"
    )
    @app_commands.describe(
        schedule_id="Schedule ID (8 chars)",
        new_time="Time: 10m / 2h / 1d OR 'YYYY-MM-DD HH:MM' (UTC)"
    )
    async def schembedtime(self, interaction: discord.Interaction, schedule_id: str, new_time: str):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        new_dt = self.parse_time(new_time)
        if not new_dt:
            return await interaction.response.send_message(
                "❌ Invalid time format.\nUse: `10m / 2h / 1d` OR `YYYY-MM-DD HH:MM` (UTC).",
                ephemeral=True
            )

        result = scheduled_embeds_col.find_one_and_update(
            {"guild_id": interaction.guild.id, "schedule_id": schedule_id},
            {"$set": {"send_time": new_dt}}
        )

        if not result:
            return await interaction.response.send_message("❌ Invalid schedule ID.", ephemeral=True)

        await interaction.response.send_message(
            f"⏰ Schedule `{schedule_id}` rescheduled to `{new_dt}` (UTC).",
            ephemeral=True
        )

    # ================= RUNNER (SAME CORE LOGIC) =================
    @tasks.loop(seconds=20)
    async def scheduler(self):
        now = datetime.utcnow()

        data = list(scheduled_embeds_col.find({
            "send_time": {"$lte": now}
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

            # delete after send
            scheduled_embeds_col.delete_one({"_id": d["_id"]})

    @scheduler.before_loop
    async def before_scheduler(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduledEmbedsSlash(bot))
