import os
import asyncio
import datetime
import pytz
import discord
from discord.ext import commands, tasks
import googleapiclient.discovery
import googleapiclient.errors

# ================= ENV =================
YOUTUBE_API_KEY = os.getenv("NILESH_YT_API")
DISCORD_CLIP_CHANNEL_ID = int(os.getenv("CLIP_DISCORD_ID"))
YOUTUBE_CHANNEL_ID = "UCcwp3JkrWcn5kF4KKzAVqCA"


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


class Clip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=YOUTUBE_API_KEY
        )

        self.live_chat_id = None
        self.next_page_token = None
        self.stream_start_time = None
        self.current_video_id = None

        self.find_live_chat.start()

    def cog_unload(self):
        self.find_live_chat.cancel()
        self.read_chat.cancel()

    # ================= FIND LIVE STREAM =================
    @tasks.loop(seconds=30)
    async def find_live_chat(self):
        try:
            req = self.youtube.search().list(
                part="id",
                channelId=YOUTUBE_CHANNEL_ID,
                eventType="live",
                type="video",
                maxResults=1
            )
            res = req.execute()

            if not res["items"]:
                return

            video_id = res["items"][0]["id"]["videoId"]

            # Prevent duplicate attach
            if video_id == self.current_video_id:
                return

            video_req = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            )
            video_res = video_req.execute()

            details = video_res["items"][0]["liveStreamingDetails"]

            self.live_chat_id = details.get("activeLiveChatId")
            self.stream_start_time = details.get("actualStartTime")
            self.current_video_id = video_id
            self.next_page_token = None

            print(f"✅ LIVE detected: {video_id}")

            if not self.read_chat.is_running():
                self.read_chat.start()

        except Exception as e:
            print("❌ Live detect error:", e)

    # ================= READ LIVE CHAT =================
    @tasks.loop(seconds=5)
    async def read_chat(self):
        if not self.live_chat_id:
            return

        try:
            req = self.youtube.liveChatMessages().list(
                liveChatId=self.live_chat_id,
                part="snippet,authorDetails",
                pageToken=self.next_page_token,
                maxResults=200,
            )

            res = await self.bot.loop.run_in_executor(None, req.execute)

            self.next_page_token = res.get("nextPageToken")

            polling_ms = res.get("pollingIntervalMillis", 3000)
            self.read_chat.change_interval(seconds=max(1, polling_ms / 1000))

            for msg in res.get("items", []):
                author = msg["authorDetails"]["displayName"]
                text = msg["snippet"]["displayMessage"]

                is_mod = msg["authorDetails"]["isChatModerator"]
                is_owner = msg["authorDetails"]["isChatOwner"]

                if not (is_mod or is_owner):
                    continue

                if text.lower().startswith("!clip"):
                    clip_name = text[len("!clip"):].strip()
                    await self.send_clip(author, clip_name)

        except googleapiclient.errors.HttpError:
            await asyncio.sleep(10)
        except Exception as e:
            print("❌ Chat read error:", e)

    # ================= SEND CLIP =================
    async def send_clip(self, author, clip_name):
        if not self.stream_start_time or not self.current_video_id:
            return

        start_dt = datetime.datetime.fromisoformat(
            self.stream_start_time.replace("Z", "+00:00")
        )
        now = datetime.datetime.now(pytz.UTC)
        seconds = int((now - start_dt).total_seconds())

        url = f"https://www.youtube.com/watch?v={self.current_video_id}&t={seconds}s"

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


async def setup(bot):
    await bot.add_cog(Clip(bot))
