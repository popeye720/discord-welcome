import discord
from discord.ext import commands
from discord import app_commands


# ================= MODAL CLASS =================
class DMMessageModal(discord.ui.Modal):
    def __init__(self, title: str, callback, image: discord.Attachment | None = None):
        super().__init__(title=title)
        self._callback = callback
        self._image = image
        # ✅ Multi-line input
        self.message = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
            placeholder="Type your message here..."
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(interaction, self.message.value, self._image)


# ================= COG =================
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
        image="Optional image"
    )
    async def dm_user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        async def send_dm(interaction, message, image):
            embed = discord.Embed(description=message, color=discord.Color.gold())
            if image and image.content_type and image.content_type.startswith("image"):
                embed.set_thumbnail(url=image.url)
                embed.set_image(url=image.url)
            try:
                await user.send(embed=embed)
                await interaction.response.send_message(
                    f"✅ DM sent to **{user}**", ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Cannot DM this user.", ephemeral=True
                )
            except Exception:
                await interaction.response.send_message(
                    "❌ Something went wrong.", ephemeral=True
                )

        await interaction.response.send_modal(
            DMMessageModal(title=f"DM to {user}", callback=send_dm, image=image)
        )

    # ================= DM ALL =================
    @app_commands.command(
        name="dmall",
        description="Send DM to all server members (Owner only)"
    )
    @app_commands.describe(
        image="Optional image"
    )
    async def dm_all(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        async def send_dm_all(interaction, message, image):
            await interaction.response.send_message(
                "📨 Sending embed DMs to all members...", ephemeral=True
            )

            embed = discord.Embed(description=message, color=discord.Color.gold())
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
                f"✅ **DM Completed**\n📨 Sent: `{sent}` users\n❌ Failed: `{failed}` users",
                ephemeral=True
            )

        await interaction.response.send_modal(
            DMMessageModal(title="DM to All Members", callback=send_dm_all, image=image)
        )

    # ================= DM ROLE =================
    @app_commands.command(
        name="dmrole",
        description="Send DM to all members of a role (Owner only)"
    )
    @app_commands.describe(
        role="Role to DM",
        image="Optional image"
    )
    async def dm_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        image: discord.Attachment | None = None
    ):
        if not self.is_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner** can use this command.",
                ephemeral=True
            )

        async def send_dm_role(interaction, message, image):
            await interaction.response.send_message(
                f"📨 Sending DMs to role **{role.name}**...", ephemeral=True
            )

            embed = discord.Embed(description=message, color=discord.Color.gold())
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
                f"✅ **DM Role Completed**\n🎭 Role: **{role.name}**\n📨 Sent: `{sent}` users\n❌ Failed: `{failed}` users",
                ephemeral=True
            )

        await interaction.response.send_modal(
            DMMessageModal(title=f"DM to Role {role.name}", callback=send_dm_role, image=image)
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(DMAll(bot))
