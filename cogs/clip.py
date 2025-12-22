import os
import asyncio
import datetime
import pytz
import discord
from discord.ext import commands
from googleapiclient.discovery import build
import pytchat

# ================= ENV =================
YOUTUBE_API_KEY = os.getenv("NILESH_YT_API")
DISCORD_CLIP_CHANNEL_ID = int(os.getenv("CLIP_DISCORD_ID"))

YOUTUBE_CHANNEL_ID = "UCcwp3JkrWcn5kF4KKzAVqCA"

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# ================= DISCORD BUTTON =================
class ClipButton(discord.ui.View):
    def __init__(self, url):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="🎬 Open Clip",
                url=url,
                style=discord.ButtonStyle.link
            )
        )


# ================= COG =================
class Clip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self.listen_youtube_chat())

    # ================= GET LIVE VIDEO =================
    def get_live_video(self):
        try:
            req = youtube.search().list(
                part="snippet",
                channelId=YOUTUBE_CHANNEL_ID,
                eventType="live",
                type="video"
            )
            res = req.execute()

            if not res["items"]:
                return None

            video_id = res["items"][0]["id"]["videoId"]

            details = youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            ).execute()

            start_time = details["items"][0]["liveStreamingDetails"]["actualStartTime"]
            return video_id, start_time

        except Exception as e:
            print("❌ YouTube API error:", e)
            return None

    # ================= BUILD CLIP URL =================
    def build_clip_url(self, video_id, start_time):
        start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        now = datetime.datetime.now(pytz.UTC)
        seconds = int((now - start_dt).total_seconds())

        return f"https://www.youtube.com/watch?v={video_id}&t={seconds}s", seconds

    # ================= SEND TO DISCORD =================
    async def send_clip(self, author, clip_name):
        data = self.get_live_video()
        if not data:
            return

        video_id, start_time = data
        url, seconds = self.build_clip_url(video_id, start_time)

        channel = self.bot.get_channel(DISCORD_CLIP_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="📌 Livestream Clip Created",
            color=0xFF0000,
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="👤 By", value=author, inline=True)
        embed.add_field(
            name="🏷 Clip Name",
            value=clip_name if clip_name else "No name",
            inline=True
        )
        embed.add_field(name="⏱ Timestamp", value=f"{seconds}s", inline=False)

        await channel.send(embed=embed, view=ClipButton(url))

    # ================= YOUTUBE CHAT LISTENER =================
    async def listen_youtube_chat(self):
        await self.bot.wait_until_ready()
        print("🎬 YouTube Clip System Started (AUTO MODE)")

        current_video_id = None

        while True:
            live = self.get_live_video()

            # No live → wait
            if not live:
                await asyncio.sleep(30)
                continue

            video_id, _ = live

            # Same live already handled
            if video_id == current_video_id:
                await asyncio.sleep(15)
                continue

            current_video_id = video_id
            print(f"✅ New LIVE detected: {video_id}")

            try:
                chat = pytchat.create(video_id=video_id)
            except Exception as e:
                print("❌ Failed to attach live chat:", e)
                await asyncio.sleep(30)
                continue

            while chat.is_alive():
                for msg in chat.get().sync_items():
                    text = msg.message.strip()

                    # Only OWNER or MODERATOR
                    if not (msg.isChatModerator or msg.isChatOwner):
                        continue

                    if text.startswith("!clip"):
                        clip_name = text.replace("!clip", "").strip()
                        await self.send_clip(msg.author.name, clip_name)

                await asyncio.sleep(1)

            print("🔴 Stream ended → waiting for next live...")
            await asyncio.sleep(10)


# ================= SETUP =================
async def setup(bot):
    await bot.add_cog(Clip(bot))
