import discord
from discord.ext import commands, tasks
import feedparser
import os
import sqlite3

DB_PATH = "youtube_notify.db"

CHANNELS = [
    {
        "name": "NILESHYT",
        "yt_id": os.getenv("NILESHYT_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHYT_NOTIFY_CHANNEL")),
    },
    {
        "name": "NILESHPLAYS",
        "yt_id": os.getenv("NILESHPLAYS_CHANNEL_ID"),
        "discord_channel": int(os.getenv("NILESHPLAYS_NOTIFY_CHANNEL")),
    }
]

class YouTubeNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(DB_PATH)
        self.cur = self.db.cursor()

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS yt_last_video (
                channel_name TEXT PRIMARY KEY,
                video_id TEXT
            )
        """)
        self.db.commit()

    async def cog_load(self):
        # 🔒 FIRST SYNC (NO NOTIFY)
        for ch in CHANNELS:
            if not ch["yt_id"]:
                continue

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['yt_id']}"
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                continue

            latest_video = feed.entries[0].yt_videoid

            self.cur.execute(
                "INSERT OR IGNORE INTO yt_last_video (channel_name, video_id) VALUES (?, ?)",
                (ch["name"], latest_video)
            )

        self.db.commit()
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.cancel()
        self.db.close()

    @tasks.loop(minutes=1)
    async def check_youtube(self):
        for ch in CHANNELS:
            if not ch["yt_id"]:
                continue

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['yt_id']}"
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                continue

            latest = feed.entries[0]
            latest_video_id = latest.yt_videoid

            self.cur.execute(
                "SELECT video_id FROM yt_last_video WHERE channel_name = ?",
                (ch["name"],)
            )
            row = self.cur.fetchone()

            # Same video → skip
            if row and row[0] == latest_video_id:
                continue

            # ✅ NEW VIDEO DETECTED
            self.cur.execute(
                "REPLACE INTO yt_last_video (channel_name, video_id) VALUES (?, ?)",
                (ch["name"], latest_video_id)
            )
            self.db.commit()

            channel = await self.bot.fetch_channel(ch["discord_channel"])

            await channel.send(
                "@everyone\n"
                f"🎬 **New Video Uploaded!**\n"
                f"📺 {latest.title}\n"
                f"🔗 {latest.link}"
            )

    @check_youtube.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(YouTubeNotify(bot))
