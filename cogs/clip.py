from discord.ext import commands, tasks
import discord
import googleapiclient.discovery
import googleapiclient.errors
import asyncio
import os
from datetime import datetime, timezone

# 🔧 LOAD ENV VARIABLES
YOUTUBE_API_KEY = os.getenv("NILESH_YT_API")
YOUTUBE_CHANNEL_ID = os.getenv("NILESHYT_CHANNEL_ID")
LIVE_NOTIFY_CHANNEL = os.getenv("LIVE_NOTIFY_CHANNEL")

if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, LIVE_NOTIFY_CHANNEL]):
    raise RuntimeError("❌ Missing ENV variables for YouTube Live Cog")

# 🔘 BUTTON VIEW
class ClipView(discord.ui.View):
    def __init__(self, url):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="🎬 Open Clip",
                url=url,
                style=discord.ButtonStyle.link
            )
        )

class LiveChatForwarder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.youtube = googleapiclient.discovery.build(
            "youtube",
            "v3",
            developerKey=YOUTUBE_API_KEY
        )

        self.live_chat_id = None
        self.video_id = None
        self.stream_start_time = None
        self.next_page_token = None

        print("🔁 YouTube Live detector started")
        self.find_live_chat.start()

    def cog_unload(self):
        try:
            self.find_live_chat.cancel()
            self.read_chat.cancel()
        except Exception:
            pass

    # 🔍 FIND LIVE STREAM
    @tasks.loop(minutes=2)
    async def find_live_chat(self):
        try:
            if self.live_chat_id:
                return

            req = self.youtube.search().list(
                part="id",
                channelId=YOUTUBE_CHANNEL_ID,
                eventType="live",
                type="video",
                maxResults=1
            )
            res = await self.bot.loop.run_in_executor(None, req.execute)

            if not res["items"]:
                return

            self.video_id = res["items"][0]["id"]["videoId"]

            req2 = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            )
            res2 = await self.bot.loop.run_in_executor(None, req2.execute)

            details = res2["items"][0]["liveStreamingDetails"]

            self.live_chat_id = details["activeLiveChatId"]
            self.stream_start_time = datetime.fromisoformat(
                details["actualStartTime"].replace("Z", "+00:00")
            )

            self.next_page_token = None
            print("✅ Live stream connected")

            if not self.read_chat.is_running():
                self.read_chat.start()

        except Exception as e:
            print("🔥 Live detect error:", e)

    # 💬 READ LIVE CHAT
    @tasks.loop(seconds=5)
    async def read_chat(self):
        try:
            if not self.live_chat_id:
                return

            req = self.youtube.liveChatMessages().list(
                liveChatId=self.live_chat_id,
                part="snippet,authorDetails",
                pageToken=self.next_page_token,
                maxResults=200
            )

            res = await self.bot.loop.run_in_executor(None, req.execute)
            self.next_page_token = res.get("nextPageToken")

            polling_ms = res.get("pollingIntervalMillis", 5000)
            self.read_chat.change_interval(
                seconds=max(5, polling_ms / 1000)
            )

            for msg in res["items"]:
                text = msg["snippet"]["displayMessage"]
                author_details = msg["authorDetails"]

                if not text.lower().startswith("!clip"):
                    continue

                if not (
                    author_details.get("isChatOwner")
                    or author_details.get("isChatModerator")
                ):
                    continue

                msg_time = datetime.fromisoformat(
                    msg["snippet"]["publishedAt"].replace("Z", "+00:00")
                )

                seconds = int((msg_time - self.stream_start_time).total_seconds())
                timestamp = f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

                clip_name = text[5:].strip() or "No name"
                clip_url = f"https://www.youtube.com/watch?v={self.video_id}&t={seconds}s"

                channel = self.bot.get_channel(int(LIVE_NOTIFY_CHANNEL))
                if not channel:
                    continue

                role = "Owner" if author_details.get("isChatOwner") else "Moderator"

                embed = discord.Embed(
                    title="🎬 Clip Requested",
                    description=(
                        f"👤 **User** : {author_details['displayName']} ({role})\n"
                        f"🏷️ **Clip Name** : {clip_name}\n"
                        f"⏱️ **Timestamp** : `{timestamp}`"
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )

                embed.set_footer(text="YouTube Live Clip System")

                await channel.send(
                    embed=embed,
                    view=ClipView(clip_url)
                )

        except googleapiclient.errors.HttpError:
            print("⚠️ Live ended, resetting...")
            self._reset_live_state()

        except Exception as e:
            print("🔥 Chat error:", e)
            self._reset_live_state()

    # ♻️ RESET
    def _reset_live_state(self):
        self.live_chat_id = None
        self.video_id = None
        self.stream_start_time = None
        self.next_page_token = None

        if self.read_chat.is_running():
            self.read_chat.stop()

# 🔌 SETUP
async def setup(bot):
    await bot.add_cog(LiveChatForwarder(bot))
