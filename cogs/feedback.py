import discord
from discord.ext import commands
from discord import app_commands
import datetime
import uuid

from database.models import feedback_col  # ✅ ensure this exists in models.py


# ========================= MODAL (TOP 5 QUESTIONS) =========================
class FeedbackModal(discord.ui.Modal, title="📝 Feedback Form"):
    def __init__(self):
        super().__init__(timeout=300)

        # Q1
        self.q1_name = discord.ui.TextInput(
            label="1) What is your name or nickname?",
            placeholder="Enter your name...",
            style=discord.TextStyle.short,
            required=True,
            max_length=80
        )

        # Q2
        self.q2_like = discord.ui.TextInput(
            label="2) What do you like the most about this server/bot?",
            placeholder="Example: stream mode, moderation, tickets, etc.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=700
        )

        # Q3
        self.q3_problem = discord.ui.TextInput(
            label="3) What problem or disturbance do you face?",
            placeholder="Example: spam, voice disturbance, bugs, etc.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=900
        )

        # Q4
        self.q4_feature = discord.ui.TextInput(
            label="4) What new feature would make your experience better?",
            placeholder="Tell your feature idea in detail...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=900
        )

        # Q5
        self.q5_extra = discord.ui.TextInput(
            label="5) Any additional suggestion or improvement?",
            placeholder="Any extra feedback...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=900
        )

        self.add_item(self.q1_name)
        self.add_item(self.q2_like)
        self.add_item(self.q3_problem)
        self.add_item(self.q4_feature)
        self.add_item(self.q5_extra)

    async def on_submit(self, interaction: discord.Interaction):
        doc = {
            "feedback_id": str(uuid.uuid4())[:8],
            "user_id": interaction.user.id,
            "user_tag": str(interaction.user),

            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else "DM",

            "name": self.q1_name.value.strip(),
            "likes_most": self.q2_like.value.strip(),
            "problem": self.q3_problem.value.strip(),
            "new_feature": self.q4_feature.value.strip(),
            "extra_suggestion": (self.q5_extra.value or "").strip(),

            "created_at_utc": datetime.datetime.utcnow(),
        }

        try:
            feedback_col.insert_one(doc)
        except Exception:
            # Ephemeral only works in guild, not in DMs
            can_ephemeral = interaction.guild is not None
            return await interaction.response.send_message(
                "❌ Feedback save nahi ho paya. Please try again.",
                ephemeral=can_ephemeral
            )

        embed = discord.Embed(
            title="✅ Feedback Submitted",
            description="Thanks! Your feedback has been saved successfully.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="ID", value=f"`{doc['feedback_id']}`", inline=True)
        embed.add_field(name="From", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Server", value=f"`{doc['guild_name']}`", inline=False)

        can_ephemeral = interaction.guild is not None
        await interaction.response.send_message(embed=embed, ephemeral=can_ephemeral)


# ========================= COG =========================
class Feedback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # optional but recommended indexes (safe try)
        try:
            feedback_col.create_index("user_id")
            feedback_col.create_index("guild_id")
            feedback_col.create_index("created_at_utc")
        except Exception:
            pass

    @app_commands.command(
        name="feedback",
        description="Submit feedback (works in server and DMs)"
    )
    async def feedback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(FeedbackModal())
        except Exception:
            can_ephemeral = interaction.guild is not None
            try:
                await interaction.response.send_message(
                    "Please try again Later. ",
                    ephemeral=can_ephemeral
                )
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Feedback(bot))