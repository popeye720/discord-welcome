import discord
from discord.ext import commands
from database.models import forms_col, form_responses_col


# ---------------- MODAL ----------------
class RegisterModal(discord.ui.Modal, title="Server Registration"):
    name = discord.ui.TextInput(label="Your Name", max_length=50)
    age = discord.ui.TextInput(label="Your Age", max_length=2)
    reason = discord.ui.TextInput(
        label="Why do you want to join?",
        style=discord.TextStyle.paragraph
    )

    def __init__(self, guild_id, user):
        super().__init__()
        self.guild_id = guild_id
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        form_responses_col.update_one(
            {
                "guild_id": self.guild_id,
                "user_id": self.user.id
            },
            {
                "$set": {
                    "name": self.name.value,
                    "age": self.age.value,
                    "reason": self.reason.value
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            "✅ Your form has been submitted!",
            ephemeral=True
        )


# ---------------- USER VIEW ----------------
class UserFormView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="📝 Register", style=discord.ButtonStyle.success, custom_id="form_register")
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            RegisterModal(interaction.guild.id, interaction.user)
        )

    @discord.ui.button(label="❌ Delete", style=discord.ButtonStyle.danger, custom_id="form_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        deleted = form_responses_col.find_one_and_delete({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

        if not deleted:
            return await interaction.response.send_message(
                "❌ You have no form submitted.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑️ Your form has been deleted.",
            ephemeral=True
        )


# ---------------- ADMIN COMMANDS ----------------
class Forms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
    async def set_form(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID")

        forms_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"channel_id": channel_id}},
            upsert=True
        )

        embed = discord.Embed(
            title="📋 Registration Form",
            description="Click the button below to register.",
            color=discord.Color.gold()
        )

        await channel.send(embed=embed, view=UserFormView(ctx.guild.id))
        await ctx.reply("✅ Form system enabled.")

    # -------- VIEW SUBMISSION --------
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
            title="📄 Form Submission",
            color=discord.Color.blue()
        )
        embed.add_field(name="Name", value=data["name"], inline=False)
        embed.add_field(name="Age", value=data["age"], inline=False)
        embed.add_field(name="Reason", value=data["reason"], inline=False)

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Forms(bot))
