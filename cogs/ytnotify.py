import discord
from discord.ext import commands, tasks
import feedparser
import re

from database.models import ytnotify_col


CHECK_INTERVAL = 8  # minutes


def resolve_text_channel(guild, arg: str):
    if not arg:
        return None

    match = re.match(r"<#(\d+)>", arg)
    if match:
        return guild.get_channel(int(match.group(1)))

    if arg.isdigit():
        return guild.get_channel(int(arg))

    return None


def format_yt_message(channel_name, entry, mention):
    link = entry.link
    title = entry.title
    live_status = entry.get("yt_livebroadcastcontent", "none")

    if live_status == "live":
        return f"{mention}\n🔴 **{channel_name} is live!**\n{link}"

    if live_status == "upcoming":
        return None

    return (
        f"{mention}\n"
        f"📺 **{channel_name} just uploaded**\n"
        f"**{title}**\n{link}"
    )


class YTNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_feeds.start()

    def cog_unload(self):
        self.check_feeds.cancel()

    # ---------------- ADD ---------------- #

    @commands.command(name="ytnotify")
    @commands.has_permissions(administrator=True)
    async def ytnotify(
        self,
        ctx,
        channel_arg: str = None,
        yt_channel_id: str = None,
        role_id: str = None
    ):

        if not channel_arg or not yt_channel_id:
            return await ctx.reply(
                "❌ Usage: `!ytnotify #channel UCxxxx [role_id]`"
            )

        channel = resolve_text_channel(ctx.guild, channel_arg)
        if not channel or not isinstance(channel, discord.TextChannel):
            return await ctx.reply("❌ Invalid Discord channel.")

        # mention logic (🔥 ONLY NEW PART)
        if role_id:
            role = ctx.guild.get_role(int(role_id))
            if not role:
                return await ctx.reply("❌ Invalid role ID.")
            mention = role.mention
        else:
            mention = "@everyone"

        exists = ytnotify_col.find_one({
            "guild_id": ctx.guild.id,
            "yt_channel_id": yt_channel_id
        })
        if exists:
            return await ctx.reply("⚠️ This YouTube channel is already added.")

        feed = feedparser.parse(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_channel_id}"
        )

        if not feed.entries:
            return await ctx.reply("❌ Invalid YouTube channel ID.")

        latest = feed.entries[0]
        yt_channel_name = feed.feed.get("author", "Unknown Channel")

        ytnotify_col.insert_one({
            "guild_id": ctx.guild.id,
            "discord_channel_id": channel.id,
            "yt_channel_id": yt_channel_id,
            "yt_channel_name": yt_channel_name,
            "last_video_id": latest.yt_videoid,
            "mention": mention  # 🔥 STORE MENTION
        })

        msg = format_yt_message(yt_channel_name, latest, mention)
        if msg:
            await channel.send(msg)

        await ctx.reply(f"✅ `{yt_channel_name}` added → {channel.mention}")

    # ---------------- DELETE ---------------- #

    @commands.command(name="delytnotify")
    @commands.has_permissions(administrator=True)
    async def delytnotify(self, ctx, yt_channel_id: str = None):

        if not yt_channel_id:
            return await ctx.reply(
                "❌ Usage: `!delytnotify UCxxxxxxxxxxxxxxxx`"
            )

        result = ytnotify_col.find_one_and_delete({
            "guild_id": ctx.guild.id,
            "yt_channel_id": yt_channel_id
        })

        if not result:
            return await ctx.reply("❌ Channel not registered.")

        await ctx.reply("🗑️ Notification removed.")

    # ---------------- LIST ---------------- #

    @commands.command(name="listytnotify")
    @commands.has_permissions(administrator=True)
    async def listytnotify(self, ctx):

        data = list(ytnotify_col.find({
            "guild_id": ctx.guild.id
        }))

        if not data:
            return await ctx.reply("ℹ️ No YouTube notifications set.")

        msg = "**📺 YouTube Notifications:**\n"
        for i, n in enumerate(data, 1):
            msg += (
                f"{i}. **{n['yt_channel_name']}**\n"
                f" ↳ Discord: <#{n['discord_channel_id']}>\n"
                f" ↳ YT ID: `{n['yt_channel_id']}`\n"
                f" ↳ Mention: {n.get('mention', '@everyone')}\n"
            )

        await ctx.reply(msg)

    # ---------------- LOOP ---------------- #

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_feeds(self):
        data = list(ytnotify_col.find({}))

        for entry in data:
            guild = self.bot.get_guild(entry["guild_id"])
            if not guild:
                continue

            feed = feedparser.parse(
                f"https://www.youtube.com/feeds/videos.xml?channel_id={entry['yt_channel_id']}"
            )

            if not feed.entries:
                continue

            latest = feed.entries[0]
            if latest.yt_videoid == entry["last_video_id"]:
                continue

            ytnotify_col.update_one(
                {"_id": entry["_id"]},
                {"$set": {"last_video_id": latest.yt_videoid}}
            )

            channel = guild.get_channel(entry["discord_channel_id"])
            if not channel:
                continue

            mention = entry.get("mention", "@everyone")
            msg = format_yt_message(entry["yt_channel_name"], latest, mention)
            if msg:
                await channel.send(msg)

    @check_feeds.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(YTNotify(bot))
