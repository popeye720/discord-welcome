import discord
from discord.ext import commands, tasks
from discord import app_commands
import feedparser
from typing import Optional, List
from database.models import ytnotify_col

CHECK_INTERVAL = 8  # minutes


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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_feeds.start()

    def cog_unload(self):
        self.check_feeds.cancel()

    # ----------------- PERMISSION CHECK -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # ================= /ytnotify-add =================
    @app_commands.command(
        name="ytnotify-add",
        description="Add YouTube upload/live notifications"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        channel="Discord channel to send notifications",
        yt_channel_id="YouTube Channel ID (UCxxxx)",
        mention_role="Optional role to mention (default: @everyone)"
    )
    async def ytnotify_add(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        yt_channel_id: str,
        mention_role: Optional[discord.Role] = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        exists = ytnotify_col.find_one({
            "guild_id": interaction.guild.id,
            "yt_channel_id": yt_channel_id
        })
        if exists:
            return await interaction.response.send_message(
                "⚠️ This YouTube channel is already added.",
                ephemeral=True
            )

        feed = feedparser.parse(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_channel_id}"
        )

        if not feed.entries:
            return await interaction.response.send_message(
                "❌ Invalid YouTube channel ID.",
                ephemeral=True
            )

        latest = feed.entries[0]
        yt_channel_name = feed.feed.get("author", "Unknown Channel")

        mention = mention_role.mention if mention_role else "@everyone"

        ytnotify_col.insert_one({
            "guild_id": interaction.guild.id,
            "discord_channel_id": channel.id,
            "yt_channel_id": yt_channel_id,
            "yt_channel_name": yt_channel_name,
            "last_video_id": latest.yt_videoid,
            "mention": mention
        })

        msg = format_yt_message(yt_channel_name, latest, mention)
        if msg:
            await channel.send(msg)

        embed = discord.Embed(
            title="✅ YouTube Notification Added",
            description=(
                f"📺 **Channel:** {yt_channel_name}\n"
                f"📢 **Discord:** {channel.mention}\n"
                f"🔔 **Mention:** {mention}"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= /ytnotify-remove =================
    @app_commands.command(
        name="ytnotify-remove",
        description="Remove YouTube notification"
    )
    @app_commands.guild_only()
    async def ytnotify_remove(
        self,
        interaction: discord.Interaction,
        yt_channel_id: str
    ):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        result = ytnotify_col.find_one_and_delete({
            "guild_id": interaction.guild.id,
            "yt_channel_id": yt_channel_id
        })

        if not result:
            return await interaction.response.send_message(
                "❌ Channel not registered.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑️ YouTube notification removed.",
            ephemeral=True
        )

    # ================= /ytnotify-list =================
    @app_commands.command(
        name="ytnotify-list",
        description="List all YouTube notifications"
    )
    @app_commands.guild_only()
    async def ytnotify_list(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return  # silent ignore

        data = list(ytnotify_col.find({
            "guild_id": interaction.guild.id
        }))

        if not data:
            return await interaction.response.send_message(
                "ℹ️ No YouTube notifications set.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📺 YouTube Notifications",
            color=discord.Color.blurple()
        )

        for i, n in enumerate(data, 1):
            embed.add_field(
                name=f"{i}. {n['yt_channel_name']}",
                value=(
                    f"📢 <#{n['discord_channel_id']}>\n"
                    f"🆔 `{n['yt_channel_id']}`\n"
                    f"🔔 {n.get('mention', '@everyone')}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= LOOP =================
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

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(YTNotify(bot))
