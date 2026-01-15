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

def _resolve_text_channel(guild: discord.Guild, raw: str) -> Optional[discord.TextChannel]:
    if not raw:
        return None
    raw = raw.strip()

    m = re.match(r"^<#!?(\d+)>$", raw)
    if m:
        return guild.get_channel(int(m.group(1)))

    if raw.isdigit():
        return guild.get_channel(int(raw))

    return None


def _resolve_role_id(guild: discord.Guild, raw: str) -> Optional[int]:
    if not raw:
        return None
    raw = raw.strip()

    m = re.match(r"^<@&(\d+)>$", raw)
    if m:
        rid = int(m.group(1))
        return rid if guild.get_role(rid) else None

    if raw.isdigit():
        rid = int(raw)
        return rid if guild.get_role(rid) else None

    return None


def _normalize_questions(text: str) -> List[str]:
    qs = []
    for line in (text or "").splitlines():
        q = line.strip()
        if q:
            qs.append(q)
    return qs


def _build_panel_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_footer(text="Use the buttons below: Fill / Edit / Delete")
    return embed


# ----------------- USER MODAL -----------------

class DynamicModal(discord.ui.Modal):
    """
    Used for BOTH: Fill and Edit.
    Loads questions from modal doc.
    old_answers -> prefill for edit.
    """
    def __init__(
        self,
        modal_doc: Dict,
        user: discord.Member,
        old_answers: Optional[Dict[str, str]] = None
    ):
        super().__init__(title=modal_doc.get("title", "📋 Modal"))

        self.modal_doc = modal_doc
        self.user = user
        self.inputs: Dict[str, discord.ui.TextInput] = {}

        old_answers = old_answers or {}
        questions = (modal_doc.get("questions") or [])[:5]  # Discord modal max 5 fields

        for q in questions:
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
            return await safe_ephemeral(interaction, "❌ This can only be used in a server.")

        answers = {q: self.inputs[q].value for q in self.inputs.keys()}

        modal_responses_col.update_one(
            {"guild_id": guild.id, "modal_id": self.modal_doc["modal_id"], "user_id": self.user.id},
            {"$set": {"answers": answers, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )

        auto_role_id = self.modal_doc.get("auto_role")
        if auto_role_id:
            role = guild.get_role(int(auto_role_id))
            if role and role not in self.user.roles:
                try:
                    await self.user.add_roles(role, reason="Modal submitted")
                except discord.Forbidden:
                    pass
                except Exception:
                    pass

        await safe_ephemeral(interaction, "✅ **Submitted successfully!**")


# ----------------- PERSISTENT VIEW (3 BUTTONS) -----------------

class ModalPanelView(discord.ui.View):
    """
    Restart-safe view for one modal_id.
    main.py on_ready binds: bot.add_view(ModalPanelView(modal_id), message_id=panel_msg_id)
    """
    def __init__(self, modal_id: str):
        super().__init__(timeout=None)
        self.modal_id = modal_id

        self.fill_btn.custom_id = f"modal:fill:{modal_id}"
        self.edit_btn.custom_id = f"modal:edit:{modal_id}"
        self.delete_btn.custom_id = f"modal:delete:{modal_id}"

    def _get_modal(self, guild_id: int) -> Optional[Dict]:
        return modal_col.find_one({"guild_id": guild_id, "modal_id": self.modal_id})

    @discord.ui.button(label="📝 Fill", style=discord.ButtonStyle.success, custom_id="modal:fill:placeholder")
    async def fill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        modal_doc = self._get_modal(guild.id)
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ This modal is not active anymore.")

        existing = modal_responses_col.find_one(
            {"guild_id": guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        if existing:
            return await safe_ephemeral(interaction, "⚠️ You already submitted.\nUse **Edit** button.")

        try:
            await interaction.response.send_modal(DynamicModal(modal_doc, interaction.user))
        except Exception:
            await safe_ephemeral(interaction, "❌ Could not open modal (try again).")

    @discord.ui.button(label="✏️ Edit", style=discord.ButtonStyle.primary, custom_id="modal:edit:placeholder")
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        modal_doc = self._get_modal(guild.id)
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ This modal is not active anymore.")

        existing = modal_responses_col.find_one(
            {"guild_id": guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        if not existing:
            return await safe_ephemeral(interaction, "❌ You haven't submitted yet.\nUse **Fill** first.")

        try:
            await interaction.response.send_modal(
                DynamicModal(modal_doc, interaction.user, existing.get("answers", {}))
            )
        except Exception:
            await safe_ephemeral(interaction, "❌ Could not open modal (try again).")

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger, custom_id="modal:delete:placeholder")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        deleted = modal_responses_col.find_one_and_delete(
            {"guild_id": guild.id, "modal_id": self.modal_id, "user_id": interaction.user.id}
        )
        if not deleted:
            return await safe_ephemeral(interaction, "❌ No submission found to delete.")
        await safe_ephemeral(interaction, "🗑️ Your response has been deleted.")


# ----------------- ADMIN CREATE MODAL -----------------

class AdminCreateModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="📋 Create Modal Panel")
        self.bot = bot

        self.channel_input = discord.ui.TextInput(
            label="Channel ID or #mention",
            placeholder="Example: #registration or 1234567890",
            required=True,
            max_length=100
        )
        self.modal_title = discord.ui.TextInput(
            label="Panel Title",
            placeholder="Example: Welcome Modal",
            required=True,
            max_length=256
        )
        self.modal_desc = discord.ui.TextInput(
            label="Panel Description",
            style=discord.TextStyle.paragraph,
            placeholder="Explain what users should fill.",
            required=True,
            max_length=2000
        )
        self.questions = discord.ui.TextInput(
            label="Questions (max 5, one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Q1...\nQ2...\nQ3...",
            required=True,
            max_length=2000
        )
        self.auto_role = discord.ui.TextInput(
            label="Auto Role (optional) ID or @role",
            placeholder="Example: @Member or 1234567890",
            required=False,
            max_length=100
        )

        self.add_item(self.channel_input)
        self.add_item(self.modal_title)
        self.add_item(self.modal_desc)
        self.add_item(self.questions)
        self.add_item(self.auto_role)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only **Admin / Owner** can do this.")

        existing = modal_col.find_one({"guild_id": guild.id})
        if existing:
            return await safe_ephemeral(interaction, "⚠️ A modal is already active. Use `/closemodal` first.")

        channel = _resolve_text_channel(guild, self.channel_input.value)
        if not channel or not isinstance(channel, discord.TextChannel):
            return await safe_ephemeral(interaction, "❌ Invalid channel.")

        qs = _normalize_questions(self.questions.value)
        if not qs:
            return await safe_ephemeral(interaction, "❌ Please provide at least 1 question.")
        if len(qs) > 5:
            qs = qs[:5]

        auto_role_id = _resolve_role_id(guild, self.auto_role.value)

        modal_id = uuid.uuid4().hex
        embed = _build_panel_embed(self.modal_title.value.strip(), self.modal_desc.value.strip())
        view = ModalPanelView(modal_id)

        try:
            panel_msg = await channel.send(embed=embed, view=view)
        except discord.Forbidden:
            return await safe_ephemeral(interaction, "❌ I don't have permission to send message in that channel.")
        except Exception as e:
            return await safe_ephemeral(interaction, f"❌ Failed to send panel: `{e}`")

        modal_col.insert_one({
            "guild_id": guild.id,
            "modal_id": modal_id,
            "channel_id": channel.id,
            "message_id": panel_msg.id,
            "title": self.modal_title.value.strip(),
            "description": self.modal_desc.value.strip(),
            "questions": qs,
            "auto_role": auto_role_id,
            "created_by": interaction.user.id,
            "created_at": datetime.now(timezone.utc)
        })

        # runtime bind (restart-safe is done in main.py on_ready via DB loop)
        try:
            self.bot.add_view(view, message_id=panel_msg.id)
        except Exception:
            pass

        await safe_ephemeral(interaction, f"✅ Modal panel created in {channel.mention}")


# ----------------- COG -----------------

class Modals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setmodal", description="Create a modal panel (Admin/Owner only)")
    @app_commands.guild_only()
    async def setmodal(self, interaction: discord.Interaction):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only **Admin / Owner** can use this.")
        await interaction.response.send_modal(AdminCreateModal(self.bot))

    @app_commands.command(
        name="closemodal",
        description="Close the active modal panel. delete_all=True deletes all responses too."
    )
    @app_commands.describe(delete_all="True = delete all responses, False = keep responses")
    @app_commands.guild_only()
    async def closemodal(self, interaction: discord.Interaction, delete_all: bool = False):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only **Admin / Owner** can use this.")

        guild = interaction.guild
        modal_doc = modal_col.find_one({"guild_id": guild.id})
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ No active modal found.")

        # delete panel message best-effort
        try:
            channel = guild.get_channel(int(modal_doc["channel_id"]))
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    msg = await channel.fetch_message(int(modal_doc["message_id"]))
                    await msg.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
                except Exception:
                    pass
        except Exception:
            pass

        modal_col.delete_one({"guild_id": guild.id})

        if delete_all:
            deleted_count = 0
            try:
                res = modal_responses_col.delete_many({"guild_id": guild.id, "modal_id": modal_doc["modal_id"]})
                deleted_count = getattr(res, "deleted_count", 0) or 0
            except Exception:
                deleted_count = 0
            return await safe_ephemeral(interaction, f"🧹 Modal closed. Deleted **{deleted_count}** responses.")

        await safe_ephemeral(interaction, "🗑️ Modal closed. Responses kept in DB.")

    @app_commands.command(name="modalresponses", description="View all modal responses (Admin/Owner only)")
    @app_commands.guild_only()
    async def modalresponses(self, interaction: discord.Interaction):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only **Admin / Owner** can use this.")

        guild = interaction.guild
        modal_doc = modal_col.find_one({"guild_id": guild.id})
        if not modal_doc:
            return await safe_ephemeral(interaction, "❌ No active modal found.")

        responses = list(modal_responses_col.find({"guild_id": guild.id, "modal_id": modal_doc["modal_id"]}))
        if not responses:
            return await safe_ephemeral(interaction, "❌ No responses found yet.")

        await safe_ephemeral(interaction, f"📄 Found **{len(responses)}** responses. Sending embeds here (ephemeral).")

        for r in responses:
            user_id = r.get("user_id")
            member = guild.get_member(int(user_id)) if user_id else None
            name = member.mention if member else f"<@{user_id}>"

            desc = ""
            answers = r.get("answers", {}) or {}
            for q, a in answers.items():
                desc += f"**{q}**\n> {str(a)[:900]}\n\n"

            embed = discord.Embed(
                title=f"📄 Response — {name}",
                description=desc[:3900],
                color=discord.Color.blurple(),
                timestamp=r.get("updated_at") or None
            )

            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Modals(bot))
