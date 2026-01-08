import re
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from models import antilinks_col

LINK_REGEX = re.compile(r"(https?:\/\/|www\.)\S+", re.IGNORECASE)

class AntiLinks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.delete_queue = asyncio.Queue()
        self.worker_task = bot.loop.create_task(self._delete_worker())

    async def _delete_worker(self):
        while True:
            message = await self.delete_queue.get()
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            finally:
                self.delete_queue.task_done()

    # ───────────── MESSAGE LISTENER ─────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if not LINK_REGEX.search(message.content):
            return

        # Owner always allowed
        if message.author.id == message.guild.owner_id:
            return

        config = await antilinks_col.find_one({"guild_id": message.guild.id})
        if not config or not config.get("enabled"):
            return

        # Admin always allowed
        if message.author.guild_permissions.administrator:
            return

        allowed_role_id = config.get("allowed_role_id")
        if allowed_role_id:
            role = message.guild.get_role(allowed_role_id)
            if role and role in message.author.roles:
                return

        await self.delete_queue.put(message)

    # ───────────── SLASH COMMAND ─────────────
    @app_commands.command(name="antilinks", description="Enable or disable anti-links")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="on / off",
        role="Role allowed to send links (optional)"
    )
    async def antilinks(
        self,
        interaction: discord.Interaction,
        action: str,
        role: discord.Role | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        if action not in ("on", "off"):
            return await interaction.followup.send("❌ Use `on` or `off`")

        if action == "off":
            await antilinks_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"enabled": False, "allowed_role_id": None}},
                upsert=True
            )
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
