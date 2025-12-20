import discord
from discord.ext import commands, tasks
import feedparser
import os

CHANNELS = [
    {
        "name": "NILESHYT",
        "yt_id": os.getenv("NILESHYT_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHYT_NOTIFY_CHANNEL")),
        "last_video": None,
        "initialized": False
    },
    {
        "name": "NILESHPLAYS",
        "yt_id": os.getenv("NILESHPLAYS_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHPLAYS_NOTIFY_CHANNEL")),
        "last_video": None,
        "initialized": False
    }
]

class YouTubeNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.cancel()

    @tasks.loop(minutes=2) 
    async def check_youtube(self):
        for ch in CHANNELS:
            if not ch["yt_id"]:
                continue

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['yt_id']}"
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                continue

            latest = feed.entries[0]
            video_id = latest.yt_videoid

            # 🟡 First run → save only (no notify)
            if not ch["initialized"]:
                ch["last_video"] = video_id
                ch["initialized"] = True
                print(f"{ch['name']} notifier initialized")
                continue

            # 🔁 Same video
            if ch["last_video"] == video_id:
                continue

            # 🟢 NEW VIDEO FOUND
            ch["last_video"] = video_id

            channel = await self.bot.fetch_channel(ch["discord_channel"])
            title = latest.title
            video_url = latest.link

            embed = discord.Embed(
                title=title,
                url=video_url,
                color=discord.Color.red()
            )

            await channel.send(
                content="@everyone",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )

    @check_youtube.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(YouTubeNotify(bot))
