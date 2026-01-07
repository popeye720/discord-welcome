import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
import uuid

from database.models import scheduled_embeds_col


class ScheduledEmbeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler.start()

    def cog_unload(self):
        self.scheduler.cancel()

    # ---------- PERMISSION ----------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # ---------- TIME PARSER ----------
    def parse_time(self, time_str):
        if re.match(r"^\d+[mhd]$", time_str):
            value = int(time_str[:-1])
            unit = time_str[-1]
            if unit == "m":
                return datetime.utcnow() + timedelta(minutes=value)
            if unit == "h":
                return datetime.utcnow() + timedelta(hours=value)
            if unit == "d":
                return datetime.utcnow() + timedelta(days=value)

        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return None

    # ================= CREATE =================
    @commands.command(name="schembed")
    @is_admin()
    async def schedule_embed(self, ctx, channel_id: int, time: str, *, message: str):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID.")

        send_time = self.parse_time(time)
        if not send_time:
            return await ctx.reply("❌ Invalid time format.")

        ping = False
        if message.startswith("--ping"):
            if not ctx.author.guild_permissions.mention_everyone:
                return await ctx.reply("❌ You cannot ping @everyone.")
            ping = True
            message = message.replace("--ping", "", 1).strip()

        schedule_id = uuid.uuid4().hex[:8]

        scheduled_embeds_col.insert_one({
            "guild_id": ctx.guild.id,
            "schedule_id": schedule_id,
            "channel_id": channel_id,
            "send_time": send_time,
            "message": message,
            "ping": ping,
            "author_id": ctx.author.id
        })

        await ctx.reply(
            f"✅ Scheduled embed created\n"
            f"🆔 ID: `{schedule_id}`\n"
            f"⏰ Time (UTC): `{send_time}`"
        )

    # ================= LIST =================
    @commands.command(name="schembedlist")
    @is_admin()
    async def list_schedules(self, ctx):
        data = list(scheduled_embeds_col.find({
            "guild_id": ctx.guild.id
        }))

        if not data:
            return await ctx.reply("📭 No scheduled embeds.")

        desc = ""
        for d in data:
            desc += (
                f"**ID:** `{d['schedule_id']}`\n"
                f"Channel: <#{d['channel_id']}>\n"
                f"Time (UTC): `{d['send_time']}`\n\n"
            )

        embed = discord.Embed(
            title="📅 Scheduled Embeds",
            description=desc,
            color=discord.Color.gold()
        )
        await ctx.reply(embed=embed)

    # ================= DELETE =================
    @commands.command(name="schembeddelete")
    @is_admin()
    async def delete_schedule(self, ctx, schedule_id: str):
        result = scheduled_embeds_col.find_one_and_delete({
            "guild_id": ctx.guild.id,
            "schedule_id": schedule_id
        })

        if not result:
            return await ctx.reply("❌ Invalid schedule ID.")

        await ctx.reply(f"🗑️ Schedule `{schedule_id}` deleted.")

    # ================= EDIT MESSAGE =================
    @commands.command(name="schembededit")
    @is_admin()
    async def edit_schedule(self, ctx, schedule_id: str, *, new_message: str):
        ping = False
        if new_message.startswith("--ping"):
            ping = True
            new_message = new_message.replace("--ping", "", 1).strip()

        result = scheduled_embeds_col.find_one_and_update(
            {
                "guild_id": ctx.guild.id,
                "schedule_id": schedule_id
            },
            {
                "$set": {
                    "message": new_message,
                    "ping": ping
                }
            }
        )

        if not result:
            return await ctx.reply("❌ Invalid schedule ID.")

        await ctx.reply(f"✏️ Schedule `{schedule_id}` updated.")

    # ================= RESCHEDULE =================
    @commands.command(name="schembedtime")
    @is_admin()
    async def reschedule(self, ctx, schedule_id: str, new_time: str):
        new_dt = self.parse_time(new_time)
        if not new_dt:
            return await ctx.reply("❌ Invalid time format.")

        result = scheduled_embeds_col.find_one_and_update(
            {
                "guild_id": ctx.guild.id,
                "schedule_id": schedule_id
            },
            {
                "$set": {
                    "send_time": new_dt
                }
            }
        )

        if not result:
            return await ctx.reply("❌ Invalid schedule ID.")

        await ctx.reply(f"⏰ Schedule `{schedule_id}` rescheduled.")

    # ================= RUNNER =================
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

            await channel.send(
                content="@everyone" if d["ping"] else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=d["ping"]
                )
            )

            # delete after send
            scheduled_embeds_col.delete_one({"_id": d["_id"]})


async def setup(bot):
    await bot.add_cog(ScheduledEmbeds(bot))
