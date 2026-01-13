import discord
from discord.ext import commands
from discord import app_commands
import datetime
import uuid

from database.models import feedback_col  # ensure this exists


# ========================= MODAL (TOP 5 QUESTIONS) =========================
class FeedbackModal(discord.ui.Modal, title="📝 Feedback Form"):
    def __init__(self):
        super().__init__(timeout=300)

        # ✅ Labels MUST be <= 45 chars
        self.q1_name = discord.ui.TextInput(
            label="1) Name / Nickname",
            placeholder="Enter your name...",
            style=discord.TextStyle.short,
            required=True,
            max_length=80
        )

        self.q2_like = discord.ui.TextInput(
            label="2) What do you like most?",
            placeholder="Example: stream mode, moderation, tickets...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=700
        )

        self.q3_problem = discord.ui.TextInput(
            label="3) Any problem / disturbance?",
            placeholder="Example: spam, VC disturbance, bugs...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=900
        )

        self.q4_feature = discord.ui.TextInput(
            label="4) What new feature you want?",
            placeholder="Describe your feature idea...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=900
        )

        self.q5_extra = discord.ui.TextInput(
            label="5) Extra suggestion (optional)",
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
        except Exception as e:
            print("❌ feedback_col.insert_one error:", repr(e))
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

        try:
            feedback_col.create_index("user_id")
            feedback_col.create_index("guild_id")
            feedback_col.create_index("created_at_utc")
        except Exception as e:
            print("Index create error:", repr(e))

    @app_commands.command(
        name="feedback",
        description="Submit feedback (works in server and DMs)"
    )
    async def feedback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(FeedbackModal())
        except Exception as e:
            print("❌ send_modal error:", repr(e))
            can_ephemeral = interaction.guild is not None
            try:
                await interaction.response.send_message(
                    "Please try again later.",
                    ephemeral=can_ephemeral
                )
            except Exception as e2:
                print("❌ fallback send_message error:", repr(e2))


async def setup(bot: commands.Bot):
    await bot.add_cog(Feedback(bot))