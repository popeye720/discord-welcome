from discord.ext import commands, tasks
import discord
import googleapiclient.discovery
import googleapiclient.errors
import os
import asyncio
import datetime

class YouTubeClipper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.YT_API = os.getenv("NILESH_YT_API")
        self.CHANNEL_ID = os.getenv("NILESHYT_CHANNEL_ID")
        self.DISCORD_NOTIFY_CHANNEL = int(os.getenv("CLIP_DISCORD_ID"))

        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=self.YT_API
        )

        self.live_chat_id = None
        self.video_id = None
        self.next_page_token = None
        self.live_detected = False  # 🔒 print only once

        self.find_live.start()

    def cog_unload(self):
        self.find_live.cancel()
        self.read_chat.cancel()
        if hasattr(self.youtube, "close"):
            self.youtube.close()

    # 🔍 FIND LIVE STREAM (PRINT ONLY ONCE)
    @tasks.loop(seconds=30)
    async def find_live(self):
        try:
            req = self.youtube.search().list(
                part="id",
                channelId=self.CHANNEL_ID,
                eventType="live",
                type="video",
                maxResults=1
            )
            res = req.execute()

            if not res["items"]:
                return

            self.video_id = res["items"][0]["id"]["videoId"]

            req2 = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            )
            res2 = req2.execute()

            chat_id = res2["items"][0]["liveStreamingDetails"].get("activeLiveChatId")

            if chat_id and not self.live_detected:
                self.live_chat_id = chat_id
                self.live_detected = True
                print("✅ Live stream detected (clip system active)")
                self.read_chat.start()

        except Exception as e:
            print("Live detect error:", e)

    # 💬 READ CHAT FOR !clip
    @tasks.loop(seconds=5)
    async def read_chat(self):
        try:
            req = self.youtube.liveChatMessages().list(
                liveChatId=self.live_chat_id,
                part="snippet,authorDetails",
                pageToken=self.next_page_token,
                maxResults=200
            )

            res = await self.bot.loop.run_in_executor(None, req.execute)
            self.next_page_token = res.get("nextPageToken")

            for msg in res.get("items", []):
                author = msg["authorDetails"]["displayName"]
                text = msg["snippet"]["displayMessage"]
                is_owner = msg["authorDetails"]["isChatOwner"]
                is_mod = msg["authorDetails"]["isChatModerator"]

                if not (is_owner or is_mod):
                    continue

                if not text.lower().startswith("!clip"):
                    continue

                clip_name = text[5:].strip() or "No clip name"

                # ⏱️ CURRENT STREAM TIMESTAMP
                now = datetime.datetime.utcnow()
                timestamp = int(now.timestamp())

                stream_url = f"https://www.youtube.com/watch?v={self.video_id}&t={timestamp}"

                channel = self.bot.get_channel(self.DISCORD_NOTIFY_CHANNEL)
                if not channel:
                    return

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="🎬 Open Clip",
                        url=stream_url
                    )
                )

                await channel.send(
                    content=(
                        f"🎥 **Clip Created!**\n\n"
                        f"👤 By: **{author}**\n"
                        f"🏷️ Name: **{clip_name}**\n"
                        f"🔗 Stream: {stream_url}"
                    ),
                    view=view
                )

        except googleapiclient.errors.HttpError:
            await asyncio.sleep(5)
        except Exception as e:
            print("Clip chat error:", e)

async def setup(bot):
    await bot.add_cog(YouTubeClipper(bot))
