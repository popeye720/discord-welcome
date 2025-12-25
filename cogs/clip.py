from discord.ext import commands, tasks
import discord
import googleapiclient.discovery
import googleapiclient.errors
import os
import asyncio
from datetime import datetime, timezone

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
            developerKey=os.environ["NILESH_YT_API"]
        )

        self.clip_active = False
        self.live_chat_id = None
        self.video_id = None
        self.stream_start_time = None
        self.next_page_token = None

        # 🔒 PRO FIX FLAG
        self.live_found_once = False

        print("🟡 Clip system loaded (waiting for !clipactive)")

    # ===================== COMMANDS =====================

    @commands.command()
    async def clipactive(self, ctx):
        if self.clip_active:
            await ctx.send("⚠️ Clip system already active")
            return

        self.clip_active = True
        self.live_found_once = False

        if not self.find_live_chat.is_running():
            self.find_live_chat.start()

        await ctx.send("🟢 Clip system activated — finding live stream...")

    @commands.command()
    async def clipdeactive(self, ctx):
        self.clip_active = False
        self._reset_live_state(full=True)

        if self.find_live_chat.is_running():
            self.find_live_chat.stop()

        await ctx.send("🔴 Clip system deactivated")

    # 🔁 MANUAL RECHECK ONLY
    @commands.command()
    async def rechecklive(self, ctx):
        self._reset_live_state(full=False)
        self.live_found_once = False

        if not self.find_live_chat.is_running():
            self.find_live_chat.start()

        await ctx.send("🔄 Rechecking live stream manually...")

    # ===================== FIND LIVE =====================

    @tasks.loop(minutes=2)
    async def find_live_chat(self):
        if not self.clip_active:
            return

        # 🔒 ABSOLUTE SEARCH BLOCK
        if self.live_found_once or self.live_chat_id or self.video_id:
            return

        try:
            req = self.youtube.search().list(
                part="id",
                channelId=os.environ["NILESHYT_CHANNEL_ID"],
                eventType="live",
                type="video",
                maxResults=1
            )
            res = req.execute()

            if not res["items"]:
                print("🔍 No live stream found")
                return

            self.video_id = res["items"][0]["id"]["videoId"]

            req2 = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            )
            res2 = req2.execute()

            details = res2["items"][0]["liveStreamingDetails"]

            self.live_chat_id = details["activeLiveChatId"]
            self.stream_start_time = datetime.fromisoformat(
                details["actualStartTime"].replace("Z", "+00:00")
            )

            self.next_page_token = None
            self.live_found_once = True

            print("✅ Live found — clip listening started")

            if not self.read_chat.is_running():
                self.read_chat.start()

        except Exception as e:
            print("🔥 Live find error:", e)

    # ===================== READ CHAT =====================

    @tasks.loop(seconds=5)
    async def read_chat(self):
        if not self.clip_active or not self.live_chat_id:
            return

        try:
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
                author = msg["authorDetails"]

                if not text.lower().startswith("!clip"):
                    continue

                if not (author.get("isChatOwner") or author.get("isChatModerator")):
                    continue

                msg_time = datetime.fromisoformat(
                    msg["snippet"]["publishedAt"].replace("Z", "+00:00")
                )

                seconds = int((msg_time - self.stream_start_time).total_seconds())
                timestamp = f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

                clip_name = text[5:].strip() or "No name"
                clip_url = f"https://www.youtube.com/watch?v={self.video_id}&t={seconds}s"

                channel = self.bot.get_channel(
                    int(os.environ["LIVE_NOTIFY_CHANNEL"])
                )
                if not channel:
                    continue

                role = "Owner" if author.get("isChatOwner") else "Moderator"

                embed = discord.Embed(
                    title="🎬 Clip Requested",
                    description=(
                        f"👤 **User** : {author['displayName']} ({role})\n"
                        f"🏷️ **Clip Name** : {clip_name}\n"
                        f"⏱️ **Timestamp** : `{timestamp}`"
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )

                embed.set_footer(text="YouTube Live Clip System")

                await channel.send(embed=embed, view=ClipView(clip_url))

        except googleapiclient.errors.HttpError:
            print("⚠️ Live ended — waiting for manual recheck")
            self._reset_live_state(full=False)

        except Exception as e:
            print("🔥 Chat error:", e)
            self._reset_live_state(full=False)

    # ===================== RESET =====================

    def _reset_live_state(self, full=False):
        self.live_chat_id = None
        self.video_id = None
        self.stream_start_time = None
        self.next_page_token = None

        if full:
            self.live_found_once = False

        if self.read_chat.is_running():
            self.read_chat.stop()

# ===================== LOAD COG =====================

async def setup(bot):
    await bot.add_cog(LiveChatForwarder(bot))
