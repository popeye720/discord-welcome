import re
import io
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageColor

from database.models import color_col
from utils.embed_color import create_embed  # 👈 helper import

HEX_REGEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")


class ColorGenerator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================= PERMISSION CHECK =================
    async def is_admin_or_owner(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if interaction.user.id == interaction.guild.owner_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    # ================= /color-setup =================
    @app_commands.command(
        name="color-setup",
        description="Setup channel for /color command"
    )
    @app_commands.describe(channel="Channel where /color will work")
    async def color_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        # 📩 Send info embed in selected channel
        info_embed = create_embed(
            title="🎨 Color Generator",
            description=(
                "Use `/color` command to generate a color image.\n\n"
                "**Examples:**\n"
                "• `/color red`\n"
                "• `/color #FF0000`\n"
                "• `/color rgb(255, 0, 0)`\n\n"
                "You can use any **color name**, **HEX code**, or **RGB value**.\n"
                "The bot will generate a **1920×1080** color image and send it in the same channel. 🎨"
            )
        )

        msg = await channel.send(embed=info_embed)

        # 💾 Store in DB
        color_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "channel_id": channel.id,
                    "info_message_id": msg.id
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ **Color Generator Enabled**\n"
            f"🎯 Channel: {channel.mention}",
            ephemeral=True
        )

    # ================= /disable-color =================
    @app_commands.command(
        name="disable-color",
        description="Disable Color Generator system"
    )
    async def disable_color(self, interaction: discord.Interaction):
        if not await self.is_admin_or_owner(interaction):
            return await interaction.response.send_message(
                "❌ Only **Admin or Server Owner** can use this command.",
                ephemeral=True
            )

        data = color_col.find_one({"guild_id": interaction.guild.id})
        if not data:
            return await interaction.response.send_message(
                "⚠️ Color Generator is already **DISABLED**.",
                ephemeral=True
            )

        # 🗑️ Delete info embed message
        channel = interaction.guild.get_channel(data.get("channel_id"))
        if channel and data.get("info_message_id"):
            try:
                msg = await channel.fetch_message(data["info_message_id"])
                await msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        color_col.delete_one({"guild_id": interaction.guild.id})

        await interaction.response.send_message(
            "🛑 **Color Generator Disabled Successfully**.",
            ephemeral=True
        )

    # ================= /color =================
    @app_commands.command(
        name="color",
        description="Generate color image using name or HEX"
    )
    @app_commands.describe(
        value="Color name (red, skyblue) or HEX (#FF0000)"
    )
    async def color(
        self,
        interaction: discord.Interaction,
        value: str
    ):
        if not interaction.guild:
            return

        data = color_col.find_one({"guild_id": interaction.guild.id})

        # ❌ Not setup
        if not data:
            return await interaction.response.send_message(
                "⚠️ **Color system is not setup yet.**\n"
                "Ask an **Admin** to use `/color-setup` first.",
                ephemeral=True
            )

        # ❌ Wrong channel
        if interaction.channel.id != data["channel_id"]:
            channel = interaction.guild.get_channel(data["channel_id"])
            return await interaction.response.send_message(
                f"❌ Please use this command in {channel.mention}.",
                ephemeral=True
            )

        # 🎨 Parse color
        try:
            rgb = ImageColor.getrgb(value.strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Invalid color.\n"
                "Use **color name**, **HEX**, or **RGB** value.",
                ephemeral=True
            )

        hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)

        # 🖼️ Create image
        img = Image.new("RGB", (1920, 1080), rgb)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename="color.png")

        embed = discord.Embed(
            title="🎨 Color Generator",
            description=(
                f"**Input:** `{value}`\n"
                f"**HEX:** `{hex_code}`\n"
                f"**RGB:** `{rgb}`\n"
                f"**Size:** `1920 x 1080`"
            ),
            color=int(hex_code.replace("#", ""), 16)
        )
        embed.set_image(url="attachment://color.png")

        await interaction.response.send_message(
            embed=embed,
            file=file
        )


# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(ColorGenerator(bot))
