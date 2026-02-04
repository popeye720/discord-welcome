import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from discord import app_commands

from database.models import modal_col, modal_responses_col
from utils.interaction import safe_ephemeral
from utils.permissions import is_admin_or_guild_owner


# ----------------- HELPERS -----------------

def _resolve_role_id(guild: discord.Guild, raw: str) -> Optional[int]:
    """
    ONLY accepts ROLE ID (digits).
    @role / mention is NOT allowed.
    """
    if not raw:
        return None

    raw = raw.strip()
    if not raw.isdigit():
        return None

    rid = int(raw)
    return rid if guild.get_role(rid) else None


def _normalize_questions(text: str) -> List[str]:
    return [q.strip() for q in (text or "").splitlines() if q.strip()]


def _build_panel_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_footer(text="Use buttons below: Fill / Edit / Delete")
    return embed


# ----------------- USER FORM MODAL -----------------

class DynamicModal(discord.ui.Modal):
    def __init__(self, modal_doc: Dict, user: discord.Member, old_answers: Optional[Dict[str, str]] = None):
        super().__init__(title=modal_doc.get("title", "📋 Form"))

        self.modal_doc = modal_doc
        self.user = user
        self.inputs: Dict[str, discord.ui.TextInput] = {}

        old_answers = old_answers or {}
        for q in (modal_doc.get("questions") or [])[:5]:
            field = discord.ui.TextInput(
                label=q[:45],
                style=discord.TextStyle.paragraph,
                default=(old_answers.get(q, "") or "")[:1000],
                required=True,
                max_length=1000
            )
            self.inputs[q] = field
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        answers = {q: self.inputs[q].value for q in self.inputs}

        modal_responses_col.update_one(
            {"guild_id": guild.id, "modal_id": self.modal_doc["modal_id"], "user_id": self.user.id},
            {"$set": {"answers": answers, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

        role_id = self.modal_doc.get("auto_role")
        if role_id:
            role = guild.get_role(int(role_id))
            if role and role not in self.user.roles:
                try:
                    await self.user.add_roles(role, reason="Form submitted")
                except Exception:
                    pass

        await safe_ephemeral(interaction, "✅ **Form submitted successfully!**")


# ----------------- PANEL VIEW -----------------

class ModalPanelView(discord.ui.View):
    def __init__(self, modal_id: str):
        super().__init__(timeout=None)
        self.modal_id = modal_id

    def _get_modal(self, guild_id: int):
        return modal_col.find_one({"guild_id": guild_id, "modal_id": self.modal_id})

    @discord.ui.button(label="📝 Fill", style=discord.ButtonStyle.success)
    async def fill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal_doc = self._get_modal(interaction.guild.id)
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ Form not active.")

        existing = modal_responses_col.find_one(
            {"guild_id": interaction.guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        if existing:
            return await safe_ephemeral(interaction, "⚠️ Already submitted. Use Edit.")

        await interaction.response.send_modal(DynamicModal(modal_doc, interaction.user))

    @discord.ui.button(label="✏️ Edit", style=discord.ButtonStyle.primary)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal_doc = self._get_modal(interaction.guild.id)
        existing = modal_responses_col.find_one(
            {"guild_id": interaction.guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        if not modal_doc or not existing:
            return await safe_ephemeral(interaction, "❌ No submission found.")

        await interaction.response.send_modal(
            DynamicModal(modal_doc, interaction.user, existing.get("answers", {}))
        )

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal_responses_col.find_one_and_delete(
            {"guild_id": interaction.guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        await safe_ephemeral(interaction, "🗑️ Your response deleted.")


# ----------------- ADMIN CREATE FORM -----------------

class AdminCreateModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="📋 Create Form Panel")
        self.bot = bot

        self.title = discord.ui.TextInput(label="Form Title", required=True)
        self.desc = discord.ui.TextInput(
            label="Form Description",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.questions = discord.ui.TextInput(
            label="Questions (max 5, one per line)",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.role = discord.ui.TextInput(
            label="Auto Role ID (optional)",
            placeholder="Example: 123456789012345678",
            required=False
        )

        for i in (self.title, self.desc, self.questions, self.role):
            self.add_item(i)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Admin only.")

        if modal_col.find_one({"guild_id": guild.id}):
            return await safe_ephemeral(interaction, "⚠️ A form already exists. Close it first.")

        qs = _normalize_questions(self.questions.value)
        role_id = _resolve_role_id(guild, self.role.value)

        modal_id = uuid.uuid4().hex
        embed = _build_panel_embed(self.title.value, self.desc.value)
        view = ModalPanelView(modal_id)

        msg = await channel.send(embed=embed, view=view)

        modal_col.insert_one({
            "guild_id": guild.id,
            "modal_id": modal_id,
            "channel_id": channel.id,
            "message_id": msg.id,
            "title": self.title.value,
            "description": self.desc.value,
            "questions": qs[:5],
            "auto_role": role_id,
            "created_at": datetime.now(timezone.utc)
        })

        self.bot.add_view(view, message_id=msg.id)
        await safe_ephemeral(interaction, "✅ Form created successfully.")


# ----------------- COG -----------------

class Forms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create-forms", description="Create a form panel in current channel")
    async def create_forms(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AdminCreateModal(self.bot))

    @app_commands.command(name="close-forms", description="Close form and delete all responses")
    async def close_forms(self, interaction: discord.Interaction):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Admin only.")

        guild = interaction.guild
        modal_doc = modal_col.find_one({"guild_id": guild.id})
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ No active form.")

        try:
            ch = guild.get_channel(modal_doc["channel_id"])
            msg = await ch.fetch_message(modal_doc["message_id"])
            await msg.delete()
        except Exception:
            pass

        modal_col.delete_one({"guild_id": guild.id})
        modal_responses_col.delete_many(
            {"guild_id": guild.id, "modal_id": modal_doc["modal_id"]}
        )

        await safe_ephemeral(interaction, "🗑️ Form closed. All responses deleted.")

    @app_commands.command(name="forms-response", description="View all form responses")
    async def forms_response(self, interaction: discord.Interaction):
        modal_doc = modal_col.find_one({"guild_id": interaction.guild.id})
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ No active form.")

        responses = list(
            modal_responses_col.find(
                {"guild_id": interaction.guild.id, "modal_id": modal_doc["modal_id"]}
            )
        )

        await safe_ephemeral(interaction, f"📄 Total responses: **{len(responses)}**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Forms(bot))
