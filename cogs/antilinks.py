import re
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from database.models import antilinks_col
from time import time

LINK_REGEX = re.compile(r"(https?:\/\/|www\.)\S+", re.IGNORECASE)

class AntiLinks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.delete_queue: asyncio.Queue[discord.Message] = asyncio.Queue(maxsize=500)
        self.worker_task = bot.loop.create_task(self._delete_worker())
        self.cache: dict[int, dict] = {}  # guild_id -> config
        self.cache_ttl = 60  # seconds

    # ───────────── CLEAN SHUTDOWN ─────────────
    def cog_unload(self):
        self.worker_task.cancel()

    # ───────────── DELETE WORKER ─────────────
    async def _delete_worker(self):
        try:
            while True:
                message = await self.delete_queue.get()
                try:
                    if message.channel.permissions_for(message.guild.me).manage_messages:
                        await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                finally:
                    self.delete_queue.task_done()
        except asyncio.CancelledError:
            pass

    # ───────────── CONFIG CACHE ─────────────
    async def _get_config(self, guild_id: int):
        cached = self.cache.get(guild_id)
        now = time()

        if cached and now - cached["ts"] < self.cache_ttl:
            return cached["data"]

        data = await antilinks_col.find_one({"guild_id": guild_id})
        self.cache[guild_id] = {"data": data, "ts": now}
        return data

    # ───────────── MESSAGE LISTENER ─────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if not LINK_REGEX.search(message.content):
            return

        if message.author.id == message.guild.owner_id:
            return

        config = await self._get_config(message.guild.id)
        if not config or not config.get("enabled"):
            return

        if message.author.guild_permissions.administrator:
            return

        allowed_role_id = config.get("allowed_role_id")
        if allowed_role_id:
            role = message.guild.get_role(allowed_role_id)
            if role and role in message.author.roles:
                return

        if not self.delete_queue.full():
            await self.delete_queue.put(message)

    # ───────────── SLASH COMMAND ─────────────
    @app_commands.command(name="antilinks", description="Enable or disable anti-links")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        action=[
            app_commands.Choice(name="on", value="on"),
            app_commands.Choice(name="off", value="off"),
        ]
    )
    async def antilinks(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: discord.Role | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        if action.value == "off":
            await antilinks_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"enabled": False, "allowed_role_id": None}},
                upsert=True
            )
            self.cache.pop(interaction.guild.id, None)
            return await interaction.followup.send("✅ Anti-links **OFF**")

        await antilinks_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "enabled": True,
                    "allowed_role_id": role.id if role else None
                }
            },
            upsert=True
        )

        self.cache.pop(interaction.guild.id, None)

        if role:
            await interaction.followup.send(
                f"✅ Anti-links **ON**\n🔓 Allowed Role: {role.mention}"
            )
        else:
            await interaction.followup.send(
                "✅ Anti-links **ON**\n🚫 Only Admins & Owner can send links"
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiLinks(bot))
