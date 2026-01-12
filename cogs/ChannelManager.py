import discord
from discord.ext import commands
from discord import app_commands

# ================= CHANNEL MANAGER =================

class ChannelManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================= PERMISSION CHECK =================
    async def can_manage(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        user = interaction.user
        return (
            user.id == guild.owner_id
            or user.guild_permissions.administrator
            or user.guild_permissions.manage_channels
        )

    def bot_can_manage(self, interaction: discord.Interaction) -> bool:
        return interaction.guild.me.guild_permissions.manage_channels

    # ================= CREATE VOICE CHANNEL =================
    @app_commands.command(name="createvc", description="Create a voice channel")
    async def create_vc(self, interaction: discord.Interaction, name: str):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        if not name.strip() or len(name) > 100:
            return await interaction.response.send_message(
                "❌ Invalid channel name.", ephemeral=True
            )

        channel = await interaction.guild.create_voice_channel(name=name)
        await interaction.response.send_message(
            f"✅ Voice channel created: **{channel.name}**", ephemeral=True
        )

    # ================= CREATE TEXT CHANNEL =================
    @app_commands.command(name="createtc", description="Create a text channel")
    async def create_tc(self, interaction: discord.Interaction, name: str):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        if not name.strip() or len(name) > 100:
            return await interaction.response.send_message(
                "❌ Invalid channel name.", ephemeral=True
            )

        channel = await interaction.guild.create_text_channel(name=name)
        await interaction.response.send_message(
            f"✅ Text channel created: **{channel.name}**", ephemeral=True
        )

    # ================= EDIT VOICE CHANNEL =================
    @app_commands.command(name="editvc", description="Rename a voice channel")
    async def edit_vc(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        new_name: str
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        if not new_name.strip():
            return await interaction.response.send_message(
                "❌ Invalid name.", ephemeral=True
            )

        await channel.edit(name=new_name)
        await interaction.response.send_message(
            f"✅ Voice channel renamed to **{new_name}**", ephemeral=True
        )

    # ================= EDIT TEXT CHANNEL =================
    @app_commands.command(name="edittc", description="Rename a text channel")
    async def edit_tc(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        new_name: str
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        if not new_name.strip():
            return await interaction.response.send_message(
                "❌ Invalid name.", ephemeral=True
            )

        await channel.edit(name=new_name)
        await interaction.response.send_message(
            f"✅ Text channel renamed to **{new_name}**", ephemeral=True
        )

    # ================= DELETE VOICE CHANNEL =================
    @app_commands.command(name="delvc", description="Delete a voice channel")
    async def delete_vc(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        await channel.delete()
        await interaction.response.send_message(
            "✅ Voice channel deleted.", ephemeral=True
        )

    # ================= DELETE TEXT CHANNEL =================
    @app_commands.command(name="deltc", description="Delete a text channel")
    async def delete_tc(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        await channel.delete()
        await interaction.response.send_message(
            "✅ Text channel deleted.", ephemeral=True
        )

    # ================= CATEGORY =================
    @app_commands.command(name="createcat", description="Create a category")
    async def create_category(self, interaction: discord.Interaction, name: str):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        category = await interaction.guild.create_category(name=name)
        await interaction.response.send_message(
            f"✅ Category created: **{category.name}**", ephemeral=True
        )

    @app_commands.command(name="editcat", description="Rename a category")
    async def edit_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        new_name: str
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        await category.edit(name=new_name)
        await interaction.response.send_message(
            f"✅ Category renamed to **{new_name}**", ephemeral=True
        )

    @app_commands.command(name="delcat", description="Delete a category")
    async def delete_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        await category.delete()
        await interaction.response.send_message(
            "✅ Category deleted.", ephemeral=True
        )

    # ================= CLEAR MESSAGES (MERGED) =================
    @app_commands.command(
        name="clearmsg",
        description="Clear messages from up to 3 text channels"
    )
    async def clearmsg(
        self,
        interaction: discord.Interaction,
        channel1: discord.TextChannel,
        channel2: discord.TextChannel | None = None,
        channel3: discord.TextChannel | None = None
    ):
        guild = interaction.guild
        if not guild:
            return

        if not (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        ):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not guild.me.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ I need **Manage Messages** permission.", ephemeral=True
            )

        channels = [c for c in (channel1, channel2, channel3) if c]
        results = []

        for channel in channels:
            try:
                deleted = await channel.purge(limit=None)
                results.append(
                    f"{channel.mention} : Deleted {len(deleted)} messages."
                )
            except discord.Forbidden:
                results.append(f"{channel.mention} : Missing permissions.")
            except discord.HTTPException:
                results.append(f"{channel.mention} : API error.")

        await interaction.response.send_message(
            "\n".join(results), ephemeral=True
        )


# ================= SETUP =================

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelManager(bot))
