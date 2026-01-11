import random
import discord
from discord.ext import commands
from discord import app_commands
from database.models import fungames_col
import asyncio


class FunGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------- PERMISSION CHECK -----------------
    async def is_admin_or_owner(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return False
        if interaction.user.id == guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ----------------- SET FUN GAMES CHANNEL -----------------
    @app_commands.command(name="fungames", description="Set fun games channel")
    async def set_fungames(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_admin_or_owner(interaction):
            return

        if fungames_col.find_one({"guild_id": interaction.guild.id}):
            return await interaction.response.send_message(
                "⚠️ Fun games already set.", ephemeral=True
            )

        # -------- EMBED HELP MESSAGE --------
        embed = discord.Embed(
            title="🎮 Fun Games",
            description="Play simple fun games using the commands below!",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🪙 /coinflip",
            value="Flip a coin and get **Heads** or **Tails**.",
            inline=False
        )
        embed.add_field(
            name="🎲 /dice",
            value="Roll a dice and get a number from **1 to 6**.",
            inline=False
        )
        embed.add_field(
            name="🎱 /8ball <question>",
            value="Ask a yes/no question and get a fun answer.",
            inline=False
        )

        embed.set_footer(text="Have fun 😄")

        help_msg = await channel.send(embed=embed)

        # -------- SAVE TO DB --------
        fungames_col.insert_one({
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "message_id": help_msg.id
        })

        await interaction.response.send_message(
            f"✅ Fun games enabled in {channel.mention}", ephemeral=True
        )

    # ----------------- DELETE FUN GAMES -----------------
    @app_commands.command(name="delfungames", description="Disable fun games")
    async def del_fungames(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return

        data = fungames_col.find_one_and_delete({"guild_id": interaction.guild.id})

        if not data:
            return await interaction.response.send_message(
                "❌ Fun games not set.", ephemeral=True
            )

        channel = interaction.guild.get_channel(data["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(data["message_id"])
                await msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

            await interaction.response.send_message(
                f"✅ Fun games disabled for {channel.mention}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ Fun games system deleted.", ephemeral=True
            )

    # ----------------- CHECK CHANNEL -----------------
    async def check_channel(self, interaction: discord.Interaction):
        data = fungames_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return False

        if interaction.channel.id != data["channel_id"]:
            try:
                await interaction.response.send_message(
                    f"❌ {interaction.user.mention} use fun commands in <#{data['channel_id']}>",
                    ephemeral=True
                )
            except discord.Forbidden:
                pass
            return False

        return True

    # ----------------- COINFLIP -----------------
    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.send_message(
            f"{interaction.user.mention} → **{random.choice(['🪙 Heads', '🪙 Tails'])}**"
        )

    # ----------------- DICE -----------------
    @app_commands.command(name="dice", description="Roll a dice")
    async def dice(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} rolled **{random.randint(1, 6)}**"
        )

    # ----------------- 8BALL -----------------
    @app_commands.command(name="8ball", description="Ask the magic 8ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        if not await self.check_channel(interaction):
            return

        responses = [
            "Yes ✅", "No ❌", "Maybe 🤔",
            "Definitely ✔️", "Ask again later 🔮"
        ]

        await interaction.response.send_message(
            f"🎱 **Question:** {question}\n"
            f"**Answer:** {random.choice(responses)}"
        )

    # ----------------- GLOBAL CHECK -----------------
    async def cog_app_command_check(self, interaction: discord.Interaction) -> bool:
        return await self.is_admin_or_owner(interaction)


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(FunGames(bot))
