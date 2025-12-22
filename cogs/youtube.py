import discord
from discord.ext import commands, tasks
import feedparser
import os

CHANNELS = [
    {
        "name": "NILESHYT",
        "yt_id": os.getenv("NILESHYT_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHYT_NOTIFY_CHANNEL")),
        "last_video": None
    },
    {
        "name": "NILESHPLAYS",
        "yt_id": os.getenv("NILESHPLAYS_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHPLAYS_NOTIFY_CHANNEL")),
        "last_video": None
    }
]

class YouTubeNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # 🔥 INITIAL SYNC (restart ke baad first upload skip nahi hogi)
        for ch in CHANNELS:
            if not ch["yt_id"]:
                continue

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['yt_id']}"
            feed = feedparser.parse(rss_url)

            if feed.entries:
                ch["last_video"] = feed.entries[0].yt_videoid

        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.cancel()

    @tasks.loop(minutes=1)  # ⚡ fast notify
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

            # Same video → skip
            if ch["last_video"] == video_id:
                continue

            # New video → notify
            ch["last_video"] = video_id

            channel = await self.bot.fetch_channel(ch["discord_channel"])

            message = (
                "@everyone\n"
                f"🎬 {latest.title}\n"
                f"🔗 {latest.link}"
            )

            await channel.send(message)

    @check_youtube.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(YouTubeNotify(bot))
