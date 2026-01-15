import discord
from discord.ext import commands
from discord import app_commands
from database.models import forms_col, form_responses_col

# ================= USER MODAL =================
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
                style=discord.TextStyle.paragraph,
                default=old_answers.get(q, ""),
                required=True,
                max_length=1000
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
            return await interaction.response.send_message("❌ Form not configured.", ephemeral=True)

        existing = form_responses_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if existing:
            return await interaction.response.send_message("⚠️ You already submitted the form.\nUse **Edit**.", ephemeral=True)

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
        existing = form_responses_col.find_one({"guild_id": interaction.guild.id, "user_id": interaction.user.id})
        if not existing:
            return await interaction.response.send_message("❌ You haven't submitted the form yet.", ephemeral=True)
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
        deleted = form_responses_col.find_one_and_delete({"guild_id": interaction.guild.id, "user_id": interaction.user.id})
        if not deleted:
            return await interaction.response.send_message("❌ No form found.", ephemeral=True)
        await interaction.response.send_message("🗑️ Your response has been deleted.", ephemeral=True)

# ================= ADMIN FORM SETUP MODAL =================
class AdminFormModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📋 Create Registration Form")
        self.add_item(discord.ui.TextInput(
            label="Channel ID or mention",
            placeholder="Enter channel where form will be sent",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Form Title",
            placeholder="Enter the form title",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Form Description",
            placeholder="Enter the description for the form",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Questions",
            style=discord.TextStyle.paragraph,
            placeholder="Type each question on a new line",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Auto Role ID (optional)",
            placeholder="Enter role ID or leave blank"
        ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_input = self.children[0].value.strip()
            title = self.children[1].value.strip()
            description = self.children[2].value.strip()
            questions_text = self.children[3].value.strip()
            auto_role_input = self.children[4].value.strip()

            if channel_input.isdigit():
                channel = interaction.guild.get_channel(int(channel_input))
            else:
                channel = interaction.guild.get_channel(int(channel_input.strip("<#>")))
            if not channel:
                return await interaction.response.send_message("❌ Invalid channel.", ephemeral=True)

            questions = [q.strip() for q in questions_text.splitlines() if q.strip()]
            if not questions:
                return await interaction.response.send_message("❌ No questions provided.", ephemeral=True)

            auto_role_id = int(auto_role_input) if auto_role_input.isdigit() else None

            embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
            msg = await channel.send(embed=embed, view=UserFormView(interaction.guild.id))

            forms_col.insert_one({
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "message_id": msg.id,
                "questions": questions,
                "auto_role": auto_role_id,
                "title": title,
                "description": description
            })

            await interaction.response.send_message("✅ Form created successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# ================= COG =================
class Forms(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="registration-form", description="Create a registration form")
    async def registration_form(self, interaction: discord.Interaction):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            return await interaction.response.send_message("❌ Only Admin or Owner can use this command.", ephemeral=True)
        await interaction.response.send_modal(AdminFormModal())

    @app_commands.command(
        name="close-registration-form",
        description="Close the active form. `delete_all=True` will delete all responses along with the form."
    )
    @app_commands.describe(
        delete_all="Whether to delete all form responses (True = delete all, False = keep responses)"
    )
    async def close_registration_form(self, interaction: discord.Interaction, delete_all: bool = False):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            return await interaction.response.send_message("❌ Only Admin or Owner can use this command.", ephemeral=True)

        form = forms_col.find_one({"guild_id": interaction.guild.id})
        if not form:
            return await interaction.response.send_message("❌ No active form.", ephemeral=True)

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

        await interaction.response.send_message("🗑️ Form closed. Responses kept.", ephemeral=True)

    @app_commands.command(name="registration-form-responses", description="View all form responses")
    async def formresponses(self, interaction: discord.Interaction):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            return await interaction.response.send_message("❌ Only Admin or Owner can use this command.", ephemeral=True)

        responses = list(form_responses_col.find({"guild_id": interaction.guild.id}))
        if not responses:
            return await interaction.response.send_message("❌ No responses found.", ephemeral=True)

        # Send one embed per response
        for r in responses:
            user = interaction.guild.get_member(r["user_id"])
            name = user.mention if user else f"<@{r['user_id']}>"
            desc = ""
            for q, a in r["answers"].items():
                desc += f"**{q}**\n> {a}\n\n"
            embed = discord.Embed(title=f"📄 Response – {name}", description=desc, color=discord.Color.blurple())
            await interaction.user.send(embed=embed)

        await interaction.response.send_message("📬 All responses sent to your DMs.", ephemeral=True)

# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Forms(bot))
