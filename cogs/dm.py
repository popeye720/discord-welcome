import discord
from discord.ext import commands
from discord import app_commands


class DMAll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 👑 OWNER CHECK
    def is_owner(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.guild
            and interaction.user.id == interaction.guild.owner_id
        )

    # ================= SINGLE DM =================
    @app_commands.command(
        name="dm",
        description="Send a DM to a single user (Owner only)"
    )
    @app_commands.describe(
        user="User to DM",
        message="Message to send",
        image="Optional image"
    )
    async def dm_user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        message: str,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        if image and image.content_type and image.content_type.startswith("image"):
            embed.set_thumbnail(url=image.url)
            embed.set_image(url=image.url)

        try:
            await user.send(embed=embed)
            await interaction.response.send_message(
                f"✅ DM sent to **{user}**",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Cannot DM this user.",
                ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "❌ Something went wrong.",
                ephemeral=True
            )

    # ================= DM ALL =================
    @app_commands.command(
        name="dmall",
        description="Send DM to all server members (Owner only)"
    )
    @app_commands.describe(
        message="Message to send",
        image="Optional image"
    )
    async def dm_all(
        self,
        interaction: discord.Interaction,
        message: str,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "📨 Sending embed DMs to all members...",
            ephemeral=True
        )

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        if image and image.content_type and image.content_type.startswith("image"):
            embed.set_thumbnail(url=image.url)
            embed.set_image(url=image.url)

        sent = 0
        failed = 0

        for member in interaction.guild.members:
            if member.bot:
                continue
            try:
                await member.send(embed=embed)
                sent += 1
            except Exception:
                failed += 1

        await interaction.followup.send(
            f"✅ **DM Completed**\n"
            f"📨 Sent: `{sent}` users\n"
            f"❌ Failed: `{failed}` users",
            ephemeral=True
        )

    # ================= DM ROLE =================
    @app_commands.command(
        name="dmrole",
        description="Send DM to all members of a role (Owner only)"
    )
    @app_commands.describe(
        role="Role to DM",
        message="Message to send",
        image="Optional image"
    )
    async def dm_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        message: str,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"📨 Sending DMs to role **{role.name}**...",
            ephemeral=True
        )

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        if image and image.content_type and image.content_type.startswith("image"):
            embed.set_thumbnail(url=image.url)
            embed.set_image(url=image.url)

        sent = 0
        failed = 0

        for member in role.members:
            if member.bot:
                continue
            try:
                await member.send(embed=embed)
                sent += 1
            except Exception:
                failed += 1

        await interaction.followup.send(
            f"✅ **DM Role Completed**\n"
            f"🎭 Role: **{role.name}**\n"
            f"📨 Sent: `{sent}` users\n"
            f"❌ Failed: `{failed}` users",
            ephemeral=True
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(DMAll(bot))
