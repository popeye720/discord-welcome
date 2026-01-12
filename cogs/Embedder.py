import discord
from discord.ext import commands
from discord import app_commands


# ================= MODAL CLASS =================
class EmbedModal(discord.ui.Modal):
    def __init__(self, title: str, callback, image: discord.Attachment | None = None, ping_everyone: bool = False):
        super().__init__(title=title)
        self._callback = callback
        self._image = image
        self._ping = ping_everyone
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
        await self._callback(interaction, self.message.value, self._image, self._ping)


# ================= COG =================
class Embedder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 👑 OWNER + ADMIN CHECK
    def can_manage(self, interaction: discord.Interaction) -> bool:
        return (
            interaction.guild
            and (
                interaction.user.id == interaction.guild.owner_id
                or interaction.user.guild_permissions.administrator
            )
        )

    # ================= SEND EMBED =================
    @app_commands.command(
        name="embedder",
        description="Send an embed to a channel"
    )
    @app_commands.describe(
        channel="Target channel",
        image="Optional image",
        ping_everyone="Ping @everyone?"
    )
    async def embedder(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        image: discord.Attachment | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.", ephemeral=True
            )

        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.", ephemeral=True
            )

        async def send_embed(interaction, message, image, ping):
            embed = discord.Embed(description=message, color=discord.Color.gold())

            if image and image.content_type and image.content_type.startswith("image"):
                embed.set_thumbnail(url=image.url)
                embed.set_image(url=image.url)

            embed.set_footer(
                text=f"Sent by {interaction.user}",
                icon_url=interaction.user.display_avatar.url
            )

            msg = await channel.send(
                content="@everyone" if ping else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=ping,
                    roles=False,
                    users=False
                )
            )
            await interaction.response.send_message(
                f"✅ Embedded message sent.\nChannel: {channel.mention}\nMessage ID: {msg.id}", ephemeral=True
            )

        await interaction.response.send_modal(
            EmbedModal(title=f"Embed to {channel.name}", callback=send_embed, image=image, ping_everyone=ping_everyone)
        )

    # ================= EDIT EMBED =================
    @app_commands.command(
        name="embededit",
        description="Edit an existing embed sent by the bot"
    )
    @app_commands.describe(
        channel="Channel of the message",
        message_id="ID of the message to edit",
        image="Optional new image",
        ping_everyone="Ping @everyone?"
    )
    async def embed_edit(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message_id: int,
        image: discord.Attachment | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.", ephemeral=True
            )

        try:
            target = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await interaction.response.send_message("❌ Message not found.", ephemeral=True)

        if target.author.id != self.bot.user.id:
            return await interaction.response.send_message("❌ Only bot messages can be edited.", ephemeral=True)

        if ping_everyone and not interaction.user.guild_permissions.mention_everyone:
            return await interaction.response.send_message(
                "❌ You don’t have permission to ping @everyone.", ephemeral=True
            )

        async def edit_embed(interaction, new_message, image, ping):
            embed = target.embeds[0] if target.embeds else discord.Embed(color=discord.Color.gold())
            embed.description = new_message
            embed.color = discord.Color.gold()

            if image and image.content_type and image.content_type.startswith("image"):
                embed.set_thumbnail(url=image.url)
                embed.set_image(url=image.url)

            embed.set_footer(
                text=f"Edited by {interaction.user}",
                icon_url=interaction.user.display_avatar.url
            )

            await target.edit(
                content="@everyone" if ping else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=ping,
                    roles=False,
                    users=False
                )
            )
            await interaction.response.send_message(f"✅ Embedded message `{message_id}` updated successfully.", ephemeral=True)

        await interaction.response.send_modal(
            EmbedModal(title=f"Edit Embed {message_id}", callback=edit_embed, image=image, ping_everyone=ping_everyone)
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Embedder(bot))
