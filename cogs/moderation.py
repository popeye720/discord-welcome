import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import os

OWNER_ID = int(os.getenv("OWNER_ID", 0))  # 👈 Railway ENV se read

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER CHECK ----------
    async def owner_only(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 This command is **Owner Only**.", ephemeral=True
            )
            return False
        return True

    # ---------------- KICK ----------------
    @app_commands.command(name="kick", description="Kick a user")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not await self.owner_only(interaction):
            return

        try:
            # DM user
            try:
                await member.send(
                    f"👢 You were **kicked** from **{interaction.guild.name}**\n"
                    f"📝 Reason: {reason}"
                )
            except:
                pass

            await member.kick(reason=reason)
            await interaction.response.send_message(
                f"✅ **{member}** has been kicked.\n📝 Reason: {reason}"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {e}", ephemeral=True
            )

    # ---------------- BAN ----------------
    @app_commands.command(name="ban", description="Ban a user")
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not await self.owner_only(interaction):
            return

        try:
            try:
                await member.send(
                    f"🔨 You were **banned** from **{interaction.guild.name}**\n"
                    f"📝 Reason: {reason}"
                )
            except:
                pass

            await member.ban(reason=reason)
            await interaction.response.send_message(
                f"✅ **{member}** has been banned.\n📝 Reason: {reason}"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {e}", ephemeral=True
            )

    # ---------------- TIMEOUT ----------------
    @app_commands.command(name="timeout", description="Timeout a user (minutes)")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int,
        reason: str = "No reason provided",
    ):
        if not await self.owner_only(interaction):
            return

        try:
            duration = timedelta(minutes=minutes)

            try:
                await member.send(
                    f"⏳ You were **timed out** in **{interaction.guild.name}**\n"
                    f"⏱ Duration: {minutes} minutes\n"
                    f"📝 Reason: {reason}"
                )
            except:
                pass

            await member.timeout(duration, reason=reason)
            await interaction.response.send_message(
                f"⏳ **{member}** timed out for **{minutes} minutes**.\n📝 Reason: {reason}"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {e}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
