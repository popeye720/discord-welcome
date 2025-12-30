import discord
from discord.ext import commands, tasks
import feedparser
import datetime

from database.models import yt_notify_col, yt_last_col

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


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
        role_id: int = None  # optional
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

        yt_last_col.delete_one({
            "guild_id": ctx.guild.id,
            "youtube_channel_id": youtube_channel_id
        })

        await ctx.reply("YouTube notification removed successfully.")

    # ================= CHECK LOOP =================

    @tasks.loop(minutes=1)
    async def check_youtube(self):
        configs = yt_notify_col.find({})

        for cfg in configs:
            rss_url = YOUTUBE_RSS.format(cfg["youtube_channel_id"])
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                continue

            entry = feed.entries[0]
            video_id = entry.yt_videoid

            last = yt_last_col.find_one({
                "guild_id": cfg["guild_id"],
                "youtube_channel_id": cfg["youtube_channel_id"]
            })

            if last and last["video_id"] == video_id:
                continue

            # 🔥 live detection
            is_live = "live" in entry.get("yt_videoavailability", "").lower()

            # skip scheduled streams
            if "scheduled" in entry.title.lower():
                continue

            yt_last_col.update_one(
                {
                    "guild_id": cfg["guild_id"],
                    "youtube_channel_id": cfg["youtube_channel_id"]
                },
                {
                    "$set": {
                        "video_id": video_id,
                        "timestamp": datetime.datetime.utcnow()
                    }
                },
                upsert=True
            )

            guild = self.bot.get_guild(cfg["guild_id"])
            if not guild:
                continue

            for ch_cfg in cfg.get("discord_channels", []):
                channel = guild.get_channel(ch_cfg["channel_id"])
                if not channel:
                    continue

                # 🔔 mention logic
                if ch_cfg.get("role_id"):
                    role = guild.get_role(ch_cfg["role_id"])
                    mention = role.mention if role else "@everyone"
                else:
                    mention = "@everyone"

                if is_live:
                    msg = (
                        f"{mention}\n"
                        "**LIVE NOW**\n"
                        f"{entry.title}\n"
                        f"{entry.link}"
                    )
                else:
                    msg = (
                        f"{mention}\n"
                        "**New Video Uploaded**\n"
                        f"{entry.title}\n"
                        f"{entry.link}"
                    )

                await channel.send(msg)

    @check_youtube.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(YouTubeNotify(bot))
