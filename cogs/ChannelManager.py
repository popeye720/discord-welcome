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

    # ================= COMMAND GROUP =================
    channel = app_commands.Group(
        name="channel",
        description="Manage server channels"
    )

    # ================= CREATE =================
    @channel.command(name="create", description="Create a channel")
    @app_commands.describe(
        type="voice / text / category",
        name="Channel name"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        type: str,
        name: str
    ):
        if not await self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not self.bot_can_manage(interaction):
            return await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.", ephemeral=True
            )

        type = type.lower()
        guild = interaction.guild

        if type == "voice":
            channel = await guild.create_voice_channel(name=name)
        elif type == "text":
            channel = await guild.create_text_channel(name=name)
        elif type == "category":
            channel = await guild.create_category(name=name)
        else:
            return await interaction.response.send_message(
                "❌ Type must be `voice`, `text`, or `category`.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Created **{channel.name}** ({type})",
            ephemeral=True
        )

    # ================= EDIT =================
    @channel.command(name="edit", description="Rename a channel")
    async def edit(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
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

        await channel.edit(name=new_name)
        await interaction.response.send_message(
            f"✅ Channel renamed to **{new_name}**",
            ephemeral=True
        )

    # ================= DELETE =================
    @channel.command(name="delete", description="Delete a channel")
    async def delete(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel
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
            "✅ Channel deleted.",
            ephemeral=True
        )

    # ================= CLEAR MESSAGES =================
    @channel.command(
        name="clear",
        description="Clear messages from up to 3 text channels"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        channel1: discord.TextChannel,
        channel2: discord.TextChannel | None = None,
        channel3: discord.TextChannel | None = None
    ):
        guild = interaction.guild

        if not (
            interaction.user.id == guild.owner_id
            or interaction.user.guild_permissions.administrator
        ):
            return await interaction.response.send_message(
                "❌ You do not have permission.", ephemeral=True
            )

        if not guild.me.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ I need **Manage Messages** permission.",
                ephemeral=True
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
            "\n".join(results),
            ephemeral=True
        )


# ================= SETUP =================

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelManager(bot))
    bot.tree.add_command(ChannelManager.channel)
