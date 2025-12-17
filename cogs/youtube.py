from discord.ext import commands, tasks
import googleapiclient.discovery
import os

# ----------- ENV VARIABLES -----------
YT_API = os.getenv("NILESH_YT_API")
YT_CHANNEL_ID = os.getenv("NILESHYT_CHANNEL_ID")
YT_NOTIFY_CHANNEL = os.getenv("NILESHYT_NOTIFY_CHANNEL")

PLAYS_API = os.getenv("NILESHPLAYS_API")
PLAYS_CHANNEL_ID = os.getenv("NILESHPLAYS_CHANNEL_ID")
PLAYS_NOTIFY_CHANNEL = os.getenv("NILESHPLAYS_NOTIFY_CHANNEL")


# ---------------------- NILESH YT NOTIFIER ----------------------
class YouTubeNotifierYT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=YT_API
        )
        self.last_video = None
        self.check_yt.start()

    @tasks.loop(minutes=1)
    async def check_yt(self):
        try:
            req = self.youtube.search().list(
                part="snippet",
                channelId=YT_CHANNEL_ID,
                maxResults=1,
                order="date"
            )
            res = req.execute()

            item = res["items"][0]
            video_id = item["id"].get("videoId")
            title = item["snippet"]["title"]

            if not video_id or video_id == self.last_video:
                return

            self.last_video = video_id
            channel = self.bot.get_channel(int(YT_NOTIFY_CHANNEL))

            if channel:
                await channel.send(
                    f"@everyone\n**{title}**\nhttps://youtu.be/{video_id}"
                )

        except Exception as e:
            print("YT Notifier Error:", e)


# ---------------------- NILESH PLAYS NOTIFIER ----------------------
class YouTubeNotifierPlays(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=PLAYS_API
        )
        self.last_video = None
        self.check_plays.start()

    @tasks.loop(minutes=1)
    async def check_plays(self):
        try:
            req = self.youtube.search().list(
                part="snippet",
                channelId=PLAYS_CHANNEL_ID,
                maxResults=1,
                order="date"
            )
            res = req.execute()

            item = res["items"][0]
            video_id = item["id"].get("videoId")
            title = item["snippet"]["title"]

            if not video_id or video_id == self.last_video:
                return

            self.last_video = video_id
            channel = self.bot.get_channel(int(PLAYS_NOTIFY_CHANNEL))

            if channel:
                await channel.send(
                    f"@everyone\n**{title}**\nhttps://youtu.be/{video_id}"
                )

        except Exception as e:
            print("Plays Notifier Error:", e)


async def setup(bot):
    await bot.add_cog(YouTubeNotifierYT(bot))
    await bot.add_cog(YouTubeNotifierPlays(bot))
