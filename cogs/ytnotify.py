import discord
from discord.ext import commands, tasks
from discord import app_commands
import feedparser
from typing import Optional
from database.models import ytnotify_col

# ================= CONFIG =================
CHECK_INTERVAL = 8  # minutes

# ================= EMBED COLOR =================
EMBED_COLOR = discord.Color.from_rgb(2, 102, 255)

def create_embed(
    title: str | None = None,
    description: str | None = None
) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=EMBED_COLOR
    )

# ================= EMBED BUILDER =================
def build_video_embed(channel_name: str, entry) -> discord.Embed:
    video_url = entry.link
    video_title = entry.title

    # thumbnail
    thumb = ""
    if "media_thumbnail" in entry:
        thumb = entry.media_thumbnail[0]["url"]
    elif "yt_videoid" in entry:
        thumb = f"https://i.ytimg.com/vi/{entry.yt_videoid}/maxresdefault.jpg"

    embed = create_embed(
        title=channel_name,
        description=f"🔗 **[{video_title}]({video_url})**"
    )

    if thumb:
        embed.set_image(url=thumb)

    return embed


class YTNotify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_feeds.start()

    def cog_unload(self):
        self.check_feeds.cancel()

    # ---------------- PERMISSION CHECK ----------------
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
    async def ytnotify_add(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        yt_channel_id: str,
        mention_role: Optional[discord.Role] = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return

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

        embed = build_video_embed(yt_channel_name, latest)
        await channel.send(content=mention, embed=embed)

        confirm = create_embed(
            title="✅ YouTube Notification Added",
            description=(
                f"📺 **Channel:** {yt_channel_name}\n"
                f"📢 **Discord:** {channel.mention}\n"
                f"🔔 **Mention:** {mention}"
            )
        )
        await interaction.response.send_message(embed=confirm, ephemeral=True)

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
            return

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
            return

        data = list(ytnotify_col.find({
            "guild_id": interaction.guild.id
        }))

        if not data:
            return await interaction.response.send_message(
                "ℹ️ No YouTube notifications set.",
                ephemeral=True
            )

        embed = create_embed(title="📺 YouTube Notifications")

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

    # ================= /force-yt-check =================
    @app_commands.command(
        name="force-yt-check",
        description="Force send latest video (no DB update)"
    )
    @app_commands.guild_only()
    async def force_yt_check(
        self,
        interaction: discord.Interaction,
        yt_channel_id: str
    ):
        if not await self.is_admin_or_owner(interaction):
            return

        entry = ytnotify_col.find_one({
            "guild_id": interaction.guild.id,
            "yt_channel_id": yt_channel_id
        })

        if not entry:
            return await interaction.response.send_message(
                "❌ This YouTube channel is not set up.",
                ephemeral=True
            )

        feed = feedparser.parse(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_channel_id}"
        )
        if not feed.entries:
            return await interaction.response.send_message(
                "❌ No videos found.",
                ephemeral=True
            )

        latest = feed.entries[0]
        channel = interaction.guild.get_channel(entry["discord_channel_id"])
        if not channel:
            return

        embed = build_video_embed(entry["yt_channel_name"], latest)
        await channel.send(content=entry.get("mention", "@everyone"), embed=embed)

        await interaction.response.send_message(
            "✅ Latest video sent (force).",
            ephemeral=True
        )

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

            embed = build_video_embed(entry["yt_channel_name"], latest)
            await channel.send(
                content=entry.get("mention", "@everyone"),
                embed=embed
            )

    @check_feeds.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(YTNotify(bot))
