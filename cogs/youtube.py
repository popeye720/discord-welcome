import discord
from discord.ext import commands, tasks
import feedparser
import datetime

from database.models import yt_notify_col, yt_last_col

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

# bot start time (IMPORTANT)
BOT_START_TIME = datetime.datetime.utcnow()


class YouTubeNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.cancel()

    # ================= OWNER COMMANDS =================

    @commands.command(name="ytnotify")
    async def add_notify(
        self,
        ctx,
        discord_channel_id: int,
        youtube_channel_id: str,
        role_id: int = None
    ):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("Only the server owner can use this command.")

        yt_notify_col.update_one(
            {
                "guild_id": ctx.guild.id,
                "youtube_channel_id": youtube_channel_id
            },
            {
                "$addToSet": {
                    "discord_channels": {
                        "channel_id": discord_channel_id,
                        "role_id": role_id
                    }
                }
            },
            upsert=True
        )

        await ctx.reply("YouTube notification configured successfully.")

    @commands.command(name="removeytnotify")
    async def remove_notify(self, ctx, youtube_channel_id: str):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("Only the server owner can use this command.")

        yt_notify_col.delete_one({
            "guild_id": ctx.guild.id,
            "youtube_channel_id": youtube_channel_id
        })

        yt_last_col.delete_many({
            "guild_id": ctx.guild.id,
            "youtube_channel_id": youtube_channel_id
        })

        await ctx.reply("YouTube notification removed successfully.")

    # ================= LIST COMMAND =================

    @commands.command(name="ytnotifylist")
    async def ytnotifylist(self, ctx):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("Only the server owner can use this command.")

        configs = list(yt_notify_col.find({"guild_id": ctx.guild.id}))
        if not configs:
            return await ctx.reply("No YouTube notification channels configured.")

        lines = []
        for cfg in configs:
            lines.append(f"**YouTube Channel ID:** `{cfg['youtube_channel_id']}`")

            for ch_cfg in cfg.get("discord_channels", []):
                ch = ctx.guild.get_channel(ch_cfg["channel_id"])
                ch_name = ch.mention if ch else f"`{ch_cfg['channel_id']}`"

                if ch_cfg.get("role_id"):
                    role = ctx.guild.get_role(ch_cfg["role_id"])
                    role_name = role.mention if role else f"`{ch_cfg['role_id']}`"
                else:
                    role_name = "@everyone"

                lines.append(f"• {ch_name} | Mention: {role_name}")

            lines.append("")

        embed = discord.Embed(
            title="YouTube Notification List",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )

        await ctx.reply(embed=embed)

    # ================= CHECK LOOP =================

    @tasks.loop(minutes=1)
    async def check_youtube(self):
        configs = yt_notify_col.find({})

        for cfg in configs:
            rss_url = YOUTUBE_RSS.format(cfg["youtube_channel_id"])
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                continue

            for entry in feed.entries:
                video_id = entry.yt_videoid

                # published time
                published = datetime.datetime(
                    *entry.published_parsed[:6],
                    tzinfo=datetime.timezone.utc
                ).replace(tzinfo=None)

                # ❌ bot start se purana video
                if published < BOT_START_TIME:
                    continue

                # ❌ scheduled stream
                if "scheduled" in entry.title.lower():
                    continue

                # ❌ already notified
                already = yt_last_col.find_one({
                    "guild_id": cfg["guild_id"],
                    "youtube_channel_id": cfg["youtube_channel_id"],
                    "video_id": video_id
                })
                if already:
                    continue

                # live detection
                is_live = "live" in entry.get("yt_videoavailability", "").lower()

                # save notification
                yt_last_col.insert_one({
                    "guild_id": cfg["guild_id"],
                    "youtube_channel_id": cfg["youtube_channel_id"],
                    "video_id": video_id,
                    "published": published,
                    "notified_at": datetime.datetime.utcnow()
                })

                guild = self.bot.get_guild(cfg["guild_id"])
                if not guild:
                    continue

                for ch_cfg in cfg.get("discord_channels", []):
                    channel = guild.get_channel(ch_cfg["channel_id"])
                    if not channel:
                        continue

                    if ch_cfg.get("role_id"):
                        role = guild.get_role(ch_cfg["role_id"])
                        mention = role.mention if role else "@everyone"
                    else:
                        mention = "@everyone"

                    if is_live:
                        msg = (
                            f"{mention}\n"
                            "🔴 **LIVE NOW**\n"
                            f"{entry.title}\n"
                            f"{entry.link}"
                        )
                    else:
                        msg = (
                            f"{mention}\n"
                            "🎥 **New Video Uploaded**\n"
                            f"{entry.title}\n"
                            f"{entry.link}"
                        )

                    await channel.send(msg)

    @check_youtube.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(YouTubeNotify(bot))
