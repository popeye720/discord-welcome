import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

from database.models import ai_config_col, ai_memory_col, system_prompt_col


FORBIDDEN_NAMES = ["nilesh", "nilu", "nilkesh"]

FORBIDDEN_REPLY = (
    "Nilesh is my developer. "
    "I cannot comment on, discuss, or store any personal information about him."
)

DEFAULT_SYSTEM_PROMPT = (
    "You are Tejas, a confident, charming and playful Indian Discord AI bot. "
)

AI_MODEL = "llama-3.1-8b-instant"
AI_TEMP = 0.3
AI_MAX_TOKENS = 300
MAX_HISTORY = 10

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------------------------------
    # PERMISSION CHECK
    # --------------------------------------------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        return (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    # --------------------------------------------------
    # AI CORE
    # --------------------------------------------------
    async def ask_ai(self, guild_id: int, user_id: int, prompt: str) -> str:
        if any(name in prompt.lower() for name in FORBIDDEN_NAMES):
            return FORBIDDEN_REPLY

        mem_doc = ai_memory_col.find_one(
            {"guild_id": guild_id, "user_id": user_id}
        ) or {}

        history = mem_doc.get("history", [])
        if not isinstance(history, list):
            history = []

        sp_doc = system_prompt_col.find_one({"_id": "default"}) or {}
        system_prompt = sp_doc.get("content") or DEFAULT_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": AI_MODEL,
                        "messages": messages,
                        "temperature": AI_TEMP,
                        "max_tokens": AI_MAX_TOKENS
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    data = await resp.json()

            if "choices" not in data:
                return "⚠️ AI is busy right now, please try again."

            reply = data["choices"][0]["message"]["content"]

        except Exception:
            return "⚠️ Something went wrong with AI. Try again later."

        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})

        ai_memory_col.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": {"history": history[-MAX_HISTORY:]}},
            upsert=True
        )

        return reply

    # --------------------------------------------------
    # /on-ai (ADMIN)
    # --------------------------------------------------
    @app_commands.command(name="on-ai", description="Enable AI in a channel")
    async def on_ai(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Owner** can use this command.",
                ephemeral=True
            )

        ai_config_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"channel_id": channel.id}},
            upsert=True
        )

        await interaction.response.send_message(
            f"💘 **Tejas AI enabled** in {channel.mention}",
            ephemeral=True
        )

    # --------------------------------------------------
    # /off-ai (ADMIN)
    # --------------------------------------------------
    @app_commands.command(name="off-ai", description="Disable AI")
    async def off_ai(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Owner** can use this command.",
                ephemeral=True
            )

        ai_config_col.delete_one({"guild_id": interaction.guild.id})

        await interaction.response.send_message(
            "💔 **Tejas AI disabled**",
            ephemeral=True
        )

    # --------------------------------------------------
    # /clear-ai-memory (ADMIN)
    # --------------------------------------------------
    @app_commands.command(
        name="clear-ai-memory",
        description="Clear ALL AI memory (admin only)"
    )
    async def clear_ai_memory(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Owner** can use this command.",
                ephemeral=True
            )

        ai_memory_col.delete_many({"guild_id": interaction.guild.id})

        await interaction.response.send_message(
            "🧹 **All AI memory cleared**",
            ephemeral=True
        )

    # --------------------------------------------------
    # /clear-my-ai-memory (USER)
    # --------------------------------------------------
    @app_commands.command(
        name="clear-my-ai-memory",
        description="Clear your own AI memory"
    )
    async def clear_my_ai_memory(self, interaction: discord.Interaction):
        config = ai_config_col.find_one(
            {"guild_id": interaction.guild.id}
        ) or {}

        if config.get("channel_id") != interaction.channel_id:
            return await interaction.response.send_message(
                "⚠️ Use this command in **AI enabled channel** only.",
                ephemeral=True
            )

        ai_memory_col.delete_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        await interaction.response.send_message(
            "🧹 **Your AI memory cleared**",
            ephemeral=True
        )

    # --------------------------------------------------
    # MESSAGE LISTENER
    # --------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = ai_config_col.find_one(
            {"guild_id": message.guild.id}
        ) or {}

        if message.channel.id != config.get("channel_id"):
            return

        prompt = message.content or ""
        if not prompt.strip():
            return

        async with message.channel.typing():
            reply = await self.ask_ai(
                message.guild.id,
                message.author.id,
                prompt
            )
            await message.reply(f"{message.author.mention} {reply}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
