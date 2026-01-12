import discord
from discord.ext import commands
from discord import app_commands
from database.models import forms_col, form_responses_col


# ================= MODAL =================
class DynamicRegisterModal(discord.ui.Modal):
    def __init__(self, guild_id, user, questions, auto_role_id=None, old_answers=None):
        super().__init__(title="📋 Registration Form")

        self.guild_id = guild_id
        self.user = user
        self.questions = questions
        self.auto_role_id = auto_role_id
        self.inputs = {}

        old_answers = old_answers or {}

        for q in questions:
            field = discord.ui.TextInput(
                label=q,
                style=discord.TextStyle.short,
                default=old_answers.get(q, ""),
                required=True,
                max_length=100
            )
            self.inputs[q] = field
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {q: self.inputs[q].value for q in self.questions}

        form_responses_col.update_one(
            {"guild_id": self.guild_id, "user_id": self.user.id},
            {"$set": {"answers": answers}},
            upsert=True
        )

        # ---------- AUTO ROLE ----------
        if self.auto_role_id:
            role = interaction.guild.get_role(self.auto_role_id)
            if role and role not in interaction.user.roles:
                try:
                    await interaction.user.add_roles(role, reason="Form submitted")
                except discord.Forbidden:
                    pass

        await interaction.response.send_message(
            "✅ **Form submitted successfully!**",
            ephemeral=True
        )


# ================= USER VIEW =================
class UserFormView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    def get_form(self, guild_id):
        return forms_col.find_one({"guild_id": guild_id})

    @discord.ui.button(label="📝 Register", style=discord.ButtonStyle.success)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        form = self.get_form(interaction.guild.id)
        if not form:
            return await interaction.response.send_message(
                "❌ Form not configured.",
                ephemeral=True
            )

        existing = form_responses_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if existing:
            return await interaction.response.send_message(
                "⚠️ You already submitted the form.\nUse **Edit**.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            DynamicRegisterModal(
                interaction.guild.id,
                interaction.user,
                form["questions"],
                form.get("auto_role")
            )
        )

    @discord.ui.button(label="✏️ Edit", style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        form = self.get_form(interaction.guild.id)

        existing = form_responses_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if not existing:
            return await interaction.response.send_message(
                "❌ You haven't submitted the form yet.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            DynamicRegisterModal(
                interaction.guild.id,
                interaction.user,
                form["questions"],
                form.get("auto_role"),
                existing["answers"]
            )
        )

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        deleted = form_responses_col.find_one_and_delete({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if not deleted:
            return await interaction.response.send_message(
                "❌ No form found.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑️ **Your response has been deleted.**",
            ephemeral=True
        )


# ================= FORMS COG =================
class Forms(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------
    # ADMIN / OWNER CHECK (REFERENCE STYLE)
    # -------------------------------
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # -------------------------------
    # SET FORM
    # -------------------------------
    @app_commands.command(name="setform", description="Create a registration form")
    @app_commands.describe(
        channel="Channel where form will be sent",
        title="Embed title",
        description="Embed description",
        questions="Format: --q Question\n--ans",
        auto_role="Role given after submit"
    )
    async def setform(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        questions: str,
        auto_role: discord.Role | None = None
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        if forms_col.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "❌ A form already exists.\nUse `/closeform` first.",
                ephemeral=True
            )

        lines = [l.strip() for l in questions.splitlines() if l.strip()]
        parsed = []

        i = 0
        while i < len(lines):
            if not lines[i].startswith("--q"):
                return await interaction.response.send_message(
                    "❌ Invalid format.\nUse `--q Question` then `--ans`",
                    ephemeral=True
                )

            q = lines[i][3:].strip()
            if not q or i + 1 >= len(lines) or lines[i + 1] != "--ans":
                return await interaction.response.send_message(
                    "❌ Each `--q` must be followed by `--ans`.",
                    ephemeral=True
                )

            parsed.append(q)
            i += 2

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold()
        )

        msg = await channel.send(
            embed=embed,
            view=UserFormView(interaction.guild.id)
        )

        forms_col.insert_one({
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "message_id": msg.id,
            "questions": parsed,
            "auto_role": auto_role.id if auto_role else None,
            "title": title,
            "description": description
        })

        await interaction.response.send_message(
            "✅ **Form created successfully.**",
            ephemeral=True
        )

    # -------------------------------
    # CLOSE FORM
    # -------------------------------
    @app_commands.command(name="closeform", description="Close the active form")
    async def closeform(
        self,
        interaction: discord.Interaction,
        delete_all: bool = False
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        form = forms_col.find_one({"guild_id": interaction.guild.id})
        if not form:
            return await interaction.response.send_message(
                "❌ No active form.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(form["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(form["message_id"])
                await msg.delete()
            except discord.NotFound:
                pass

        forms_col.delete_one({"guild_id": interaction.guild.id})

        if delete_all:
            result = form_responses_col.delete_many({"guild_id": interaction.guild.id})
            return await interaction.response.send_message(
                f"🧹 Deleted **{result.deleted_count}** responses.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑️ Form closed. Responses kept.",
            ephemeral=True
        )

    # -------------------------------
    # VIEW RESPONSES
    # -------------------------------
    @app_commands.command(name="formresponses", description="View form responses")
    async def formresponses(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        responses = list(form_responses_col.find({"guild_id": interaction.guild.id}))
        if not responses:
            return await interaction.response.send_message(
                "❌ No responses found.",
                ephemeral=True
            )

        embeds = []
        for r in responses:
            user = interaction.guild.get_member(r["user_id"])
            name = user.mention if user else f"<@{r['user_id']}>"

            desc = ""
            for q, a in r["answers"].items():
                desc += f"**{q}**\n> {a}\n\n"

            embeds.append(
                discord.Embed(
                    title=f"📄 Response – {name}",
                    description=desc,
                    color=discord.Color.blurple()
                )
            )

        await interaction.response.send_message(
            embed=embeds[0],
            ephemeral=True
        )

    # -------------------------------
    # GLOBAL SLASH CHECK (REFERENCE)
    # -------------------------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Forms(bot))
