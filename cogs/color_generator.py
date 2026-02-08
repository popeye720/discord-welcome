import re
import io
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageColor

HEX_REGEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")

class ColorGenerator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------
    # /color COMMAND
    # -------------------------------
    @app_commands.command(
        name="color",
        description="Generate color image using any color name or HEX code"
    )
    @app_commands.describe(
        value="Any color name (red, skyblue, gold) or HEX (#FF0000)"
    )
    async def color(
        self,
        interaction: discord.Interaction,
        value: str
    ):
        value = value.strip()

        # -------------------------------
        # PARSE COLOR (NO HARD CODE)
        # -------------------------------
        try:
            rgb = ImageColor.getrgb(value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Invalid color value.\n"
                "Try **any color name** (`red`, `skyblue`, `gold`) or **HEX** (`#FF0000`).",
                ephemeral=True
            )

        # Convert RGB → HEX
        hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)

        # -------------------------------
        # CREATE IMAGE (1920x1080)
        # -------------------------------
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

        # -------------------------------
        # SEND IN SAME CHANNEL
        # -------------------------------
        await interaction.response.send_message(
            embed=embed,
            file=file
        )

# ----------------- SETUP -----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(ColorGenerator(bot))
