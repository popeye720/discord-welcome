import discord
from discord.ext import commands
from discord import app_commands

from utils.embed_color import create_embed, EMBED_COLOR


# ================= MODAL CLASS =================
class EmbedModal(discord.ui.Modal):
    def __init__(
        self,
        title: str,
        callback,
        default_text: str = "",
        image: discord.Attachment | None = None,
        ping_everyone: bool = False
    ):
        super().__init__(title=title)

        self._callback = callback
        self._image = image
        self._ping = ping_everyone

        self.message = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
            default=default_text,  # ✅ PREFILL HERE
            placeholder="Edit your embed message here..."
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(
            interaction,
            self.message.value,
            self._image,
            self._ping
        )


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
    @app_commands.command(name="embedder", description="Send an embed to a channel")
    async def embedder(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        image: discord.Attachment | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        async def send_embed(interaction, message, image, ping):
            embed = create_embed(description=message)

            if image and image.content_type and image.content_type.startswith("image"):
                embed.set_image(url=image.url)

            embed.set_footer(
                text=f"Sent by {interaction.user}",
                icon_url=interaction.user.display_avatar.url
            )

            msg = await channel.send(
                content="@everyone" if ping else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=ping)
            )

            await interaction.response.send_message(
                f"✅ Embed sent\nMessage ID: `{msg.id}`",
                ephemeral=True
            )

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Embed to {channel.name}",
                callback=send_embed,
                image=image,
                ping_everyone=ping_everyone
            )
        )

    # ================= EDIT EMBED =================
    @app_commands.command(name="embededit", description="Edit an existing embed")
    async def embed_edit(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message_id: str,
        image: discord.Attachment | None = None,
        ping_everyone: bool = False
    ):
        if not self.can_manage(interaction):
            return await interaction.response.send_message(
                "❌ Only **Server Owner or Admin** can use this command.",
                ephemeral=True
            )

        try:
            target = await channel.fetch_message(int(message_id))
        except Exception:
            return await interaction.response.send_message(
                "❌ Invalid or missing message.",
                ephemeral=True
            )

        if target.author.id != self.bot.user.id:
            return await interaction.response.send_message(
                "❌ Only bot messages can be edited.",
                ephemeral=True
            )

        old_text = (
            target.embeds[0].description
            if target.embeds and target.embeds[0].description
            else ""
        )

        async def edit_embed(interaction, new_message, image, ping):
            embed = target.embeds[0] if target.embeds else create_embed()
            embed.description = new_message
            embed.color = EMBED_COLOR

            if image and image.content_type and image.content_type.startswith("image"):
                embed.set_image(url=image.url)

            embed.set_footer(
                text=f"Edited by {interaction.user}",
                icon_url=interaction.user.display_avatar.url
            )

            await target.edit(
                content="@everyone" if ping else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=ping)
            )

            await interaction.response.send_message(
                "✅ Embed updated successfully.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            EmbedModal(
                title=f"Edit Embed {message_id}",
                callback=edit_embed,
                default_text=old_text,  # ✅ OLD CONTENT PASSED
                image=image,
                ping_everyone=ping_everyone
            )
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Embedder(bot))
