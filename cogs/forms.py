import discord
from discord.ext import commands
from database.models import forms_col, form_responses_col


# ================= MODAL =================
class DynamicRegisterModal(discord.ui.Modal):
    def __init__(self, guild_id, user, questions, old_answers=None):
        super().__init__(title="Registration Form")
        self.guild_id = guild_id
        self.user = user
        self.questions = questions
        self.inputs = {}

        old_answers = old_answers or {}

        for q in questions:
            inp = discord.ui.TextInput(
                label=q,
                style=discord.TextStyle.short,
                default=old_answers.get(q, ""),
                max_length=100
            )
            self.inputs[q] = inp
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {q: self.inputs[q].value for q in self.questions}

        form_responses_col.update_one(
            {
                "guild_id": self.guild_id,
                "user_id": self.user.id
            },
            {
                "$set": {
                    "answers": answers
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            "✅ Your form has been submitted successfully!",
            ephemeral=True
        )


# ================= USER VIEW =================
class UserFormView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(
        label="📝 Register / Edit",
        style=discord.ButtonStyle.success,
        custom_id="form_register_edit"
    )
    async def register_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        form = forms_col.find_one({"guild_id": interaction.guild.id})
        if not form:
            return await interaction.response.send_message(
                "❌ Form is not configured.",
                ephemeral=True
            )

        existing = form_responses_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        await interaction.response.send_modal(
            DynamicRegisterModal(
                interaction.guild.id,
                interaction.user,
                form["questions"],
                existing["answers"] if existing else None
            )
        )

    @discord.ui.button(
        label="❌ Delete",
        style=discord.ButtonStyle.danger,
        custom_id="form_delete"
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        deleted = form_responses_col.find_one_and_delete({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if not deleted:
            return await interaction.response.send_message(
                "❌ You have not submitted any form.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑️ Your form has been deleted.",
            ephemeral=True
        )


# ================= ADMIN COG =================
class Forms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- PERMISSION --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SET FORM --------
    @commands.command(name="setform")
    @is_admin()
    async def set_form(self, ctx, channel_id: int, *, raw: str):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID.")

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        questions = []

        i = 0
        while i < len(lines):
            if not lines[i].startswith("--q"):
                return await ctx.reply(
                    "❌ Invalid format.\n\n"
                    "**Correct Example:**\n"
                    "`!setform <channel_id>`\n"
                    "`--qTEAM NAME`\n"
                    "`--ans`\n"
                    "`--qPLAYER IGN`\n"
                    "`--ans`"
                )

            q = lines[i][3:].strip()
            if not q or i + 1 >= len(lines) or lines[i + 1] != "--ans":
                return await ctx.reply("❌ Each `--q` must be followed by `--ans`.")

            questions.append(q)
            i += 2

        if not 1 <= len(questions) <= 5:
            return await ctx.reply("❌ You can add **1 to 5 questions only**.")

        embed = discord.Embed(
            title="📋 Registration Form",
            description="Click the button below to **Register / Edit** your form.",
            color=discord.Color.gold()
        )

        msg = await channel.send(embed=embed, view=UserFormView(ctx.guild.id))

        forms_col.update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "channel_id": channel_id,
                    "message_id": msg.id,
                    "questions": questions
                }
            },
            upsert=True
        )

        await ctx.reply("✅ Form configured successfully.")

    # -------- VIEW FORM --------
    @commands.command(name="viewform")
    @is_admin()
    async def view_form(self, ctx, user: discord.Member):
        data = form_responses_col.find_one({
            "guild_id": ctx.guild.id,
            "user_id": user.id
        })

        if not data:
            return await ctx.reply("❌ No form found for this user.")

        embed = discord.Embed(
            title=f"📄 Form Submission — {user}",
            color=discord.Color.blue()
        )

        for q, ans in data["answers"].items():
            embed.add_field(name=q, value=ans or "N/A", inline=False)

        await ctx.reply(embed=embed)

    # -------- DELETE FORM --------
    @commands.command(name="delform")
    @is_admin()
    async def delete_form(self, ctx, flag: str = None):
        form = forms_col.find_one({"guild_id": ctx.guild.id})

        # delete panel if exists
        if form and "channel_id" in form and "message_id" in form:
            channel = ctx.guild.get_channel(form["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(form["message_id"])
                    await msg.delete()
                except discord.NotFound:
                    pass

        if flag == "--all":
            forms_col.delete_one({"guild_id": ctx.guild.id})
            result = form_responses_col.delete_many({
                "guild_id": ctx.guild.id
            })

            return await ctx.reply(
                f"🗑️ Form panel deleted.\n"
                f"🧹 Deleted **{result.deleted_count}** user responses."
            )

        if not form:
            return await ctx.reply("❌ No form is currently set.")

        forms_col.delete_one({"guild_id": ctx.guild.id})

        await ctx.reply(
            "🗑️ Form panel deleted. Form is now closed.\n"
            "ℹ️ User responses are still saved.\n"
            "Use `!delform --all` to delete everything."
        )


async def setup(bot):
    await bot.add_cog(Forms(bot))
