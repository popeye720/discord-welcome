import math
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

import discord
from discord.ext import commands
from discord import app_commands

from database.models import solarinfo_col
from utils.interaction import safe_ephemeral
from utils.permissions import is_admin_or_guild_owner
from utils.embed_color import create_embed


# ----------------- CONSTANTS -----------------

DAYS_IN_MONTH = 30
DAYS_IN_YEAR = 365


# ----------------- HELPERS -----------------

def _clean_number(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_units(value: float) -> str:
    return f"{_format_number(value)} units"


def _format_inr(value: float) -> str:
    return f"₹{_format_number(value)}"


def _format_capacity_from_kw(kw: float) -> str:
    if kw >= 1_000_000:
        return f"{_format_number(kw / 1_000_000)} GW"
    if kw >= 1_000:
        return f"{_format_number(kw / 1_000)} MW"
    return f"{_format_number(kw)} kW"


def _parse_capacity_to_kw(raw: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Supports:
    1kw, 1 kW, 1MW, 1000kw, 1GW, 2.5 MW, etc.
    Returns: (capacity_in_kw, error_message)
    """
    if not raw:
        return None, "❌ Solar capacity is required."

    text = raw.strip().lower().replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(kw|mw|gw)", text)

    if not match:
        return None, (
            "❌ Invalid solar capacity format.\n"
            "Examples: `1kW`, `500kW`, `1MW`, `2.5MW`, `1GW`"
        )

    value = float(match.group(1))
    unit = match.group(2)

    multiplier = {
        "kw": 1,
        "mw": 1000,
        "gw": 1_000_000
    }

    kw = value * multiplier[unit]
    return kw, None


def _parse_panel_size_to_watt(raw: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Supports:
    550W, 540 W, 0.55kW, 0.54 kW
    Returns: (panel_watt, error_message)
    """
    if not raw or not raw.strip():
        return None, None

    text = raw.strip().lower().replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(w|kw)", text)

    if not match:
        return None, "❌ Invalid panel size format. Examples: `550W`, `540W`, `0.55kW`"

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "kw":
        return value * 1000, None

    return value, None


def _build_panel_embed() -> discord.Embed:
    embed = create_embed(
        title="☀️ Solar Info Panel",
        description=(
            "Click the button below and fill in your solar plant details.\n\n"
            "**Required details:**\n"
            "• Solar Capacity\n"
            "• Per Day Generation Unit\n\n"
            "**Optional details:**\n"
            "• Grid Buying Price (INR)\n"
            "• Panel Size\n"
            "• Location / Notes"
        )
    )
    embed.add_field(
        name="📌 Supported Capacity Formats",
        value="`1kW` • `500kW` • `1MW` • `1000MW` • `1GW`",
        inline=False
    )
    embed.add_field(
        name="📌 Supported Panel Size Formats",
        value="`550W` • `540W` • `600W` • `0.55kW`",
        inline=False
    )
    embed.add_field(
        name="📌 Example",
        value=(
            "**Solar Capacity:** `1MW`\n"
            "**Per Day Generation Unit:** `4.5`\n"
            "**Grid Buying Price:** `3.5`\n"
            "**Panel Size:** `550W`"
        ),
        inline=False
    )
    embed.set_footer(text="Use the button below to calculate solar generation and income.")
    return embed


def _build_result_embed(
    user: discord.abc.User,
    capacity_raw: str,
    capacity_kw: float,
    unit_per_kw_per_day: float,
    buy_price: Optional[float],
    panel_size_watt: Optional[float],
    location_notes: Optional[str]
) -> discord.Embed:
    per_day_generation = capacity_kw * unit_per_kw_per_day
    per_month_generation = per_day_generation * DAYS_IN_MONTH
    per_year_generation = per_day_generation * DAYS_IN_YEAR

    embed = create_embed(
        title="☀️ Solar Plant Details",
        description=f"Submitted by {user.mention}"
    )

    plant_info = (
        f"**Entered Capacity:** `{capacity_raw}`\n"
        f"**Normalized Capacity:** `{_format_capacity_from_kw(capacity_kw)}`\n"
        f"**Per kW / Day Generation:** `{_format_number(unit_per_kw_per_day)} units`"
    )

    if buy_price is not None:
        plant_info += f"\n**Grid Buying Price:** `{_format_inr(buy_price)} / unit`"

    if location_notes:
        plant_info += f"\n**Location / Notes:** `{location_notes}`"

    embed.add_field(
        name="🔋 Plant Capacity",
        value=plant_info,
        inline=False
    )

    if panel_size_watt is not None and panel_size_watt > 0:
        total_panels = math.ceil((capacity_kw * 1000) / panel_size_watt)

        infra_text = (
            f"**Panel Size:** `{_format_number(panel_size_watt)}W`\n"
            f"**Total Panels:** `{_format_number(total_panels)}`"
        )

        embed.add_field(
            name="🔧 Solar Infrastructure",
            value=infra_text,
            inline=False
        )

    day_text = f"**Generation:** {_format_units(per_day_generation)}"
    month_text = f"**Generation:** {_format_units(per_month_generation)}"
    year_text = f"**Generation:** {_format_units(per_year_generation)}"

    if buy_price is not None:
        day_income = per_day_generation * buy_price
        month_income = per_month_generation * buy_price
        year_income = per_year_generation * buy_price

        day_text += f"\n**Income:** {_format_inr(day_income)}"
        month_text += f"\n**Income:** {_format_inr(month_income)}"
        year_text += f"\n**Income:** {_format_inr(year_income)}"

    embed.add_field(name="📅 Per Day", value=day_text, inline=False)
    embed.add_field(name="🗓️ Per Month", value=month_text, inline=False)
    embed.add_field(name="📈 Per Year", value=year_text, inline=False)

    embed.add_field(
        name="ℹ️ Calculation Basis",
        value=(
            f"**Monthly estimate:** {DAYS_IN_MONTH} days\n"
            f"**Yearly estimate:** {DAYS_IN_YEAR} days"
        ),
        inline=False
    )

    embed.set_footer(text="This is an estimated calculation based on the submitted values.")
    return embed


# ----------------- MODAL -----------------

class SolarInfoModal(discord.ui.Modal, title="Solar Plant Details"):
    def __init__(self, panel_doc: dict):
        super().__init__()
        self.panel_doc = panel_doc

        self.solar_capacity = discord.ui.TextInput(
            label="1) Solar Capacity",
            placeholder="Example: 1kW / 500kW / 1MW / 1GW",
            required=True,
            max_length=50
        )

        self.per_day_generation = discord.ui.TextInput(
            label="2) Solar Per Day Generation Unit",
            placeholder="Example: 4 / 5 / 6.5",
            required=True,
            max_length=20
        )

        self.grid_buying_price = discord.ui.TextInput(
            label="3) Grid Buying Price (INR) - Optional",
            placeholder="Example: 3 / 3.5 / 4",
            required=False,
            max_length=20
        )

        self.panel_size = discord.ui.TextInput(
            label="4) Panel Size - Optional",
            placeholder="Example: 550W / 540W / 0.55kW",
            required=False,
            max_length=20
        )

        self.location_notes = discord.ui.TextInput(
            label="5) Location / Notes - Optional",
            placeholder="Example: Gujarat / Factory rooftop / Residential",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=250
        )

        self.add_item(self.solar_capacity)
        self.add_item(self.per_day_generation)
        self.add_item(self.grid_buying_price)
        self.add_item(self.panel_size)
        self.add_item(self.location_notes)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "❌ This command works only in a server.",
                ephemeral=True
            )

        capacity_kw, capacity_error = _parse_capacity_to_kw(self.solar_capacity.value)
        if capacity_error:
            return await interaction.response.send_message(capacity_error, ephemeral=True)

        per_day_unit = _clean_number(self.per_day_generation.value)
        if per_day_unit is None or per_day_unit <= 0:
            return await interaction.response.send_message(
                "❌ Per day generation unit must be a valid number greater than 0.",
                ephemeral=True
            )

        buy_price = None
        if self.grid_buying_price.value and self.grid_buying_price.value.strip():
            buy_price = _clean_number(self.grid_buying_price.value)
            if buy_price is None or buy_price < 0:
                return await interaction.response.send_message(
                    "❌ Grid buying price must be a valid number.",
                    ephemeral=True
                )

        panel_size_watt = None
        if self.panel_size.value and self.panel_size.value.strip():
            panel_size_watt, panel_size_error = _parse_panel_size_to_watt(self.panel_size.value)
            if panel_size_error:
                return await interaction.response.send_message(
                    panel_size_error,
                    ephemeral=True
                )

            if panel_size_watt is not None and panel_size_watt <= 0:
                return await interaction.response.send_message(
                    "❌ Panel size must be greater than 0.",
                    ephemeral=True
                )

        location_notes = self.location_notes.value.strip() if self.location_notes.value else None

        result_embed = _build_result_embed(
            user=interaction.user,
            capacity_raw=self.solar_capacity.value.strip(),
            capacity_kw=capacity_kw,
            unit_per_kw_per_day=per_day_unit,
            buy_price=buy_price,
            panel_size_watt=panel_size_watt,
            location_notes=location_notes
        )

        setup_channel = guild.get_channel(self.panel_doc["channel_id"])
        if setup_channel is None:
            try:
                setup_channel = await guild.fetch_channel(self.panel_doc["channel_id"])
            except Exception:
                return await interaction.response.send_message(
                    "❌ Setup channel not found.",
                    ephemeral=True
                )

        await setup_channel.send(embed=result_embed)

        await interaction.response.send_message(
            "✅ Your solar details have been submitted successfully.",
            ephemeral=True
        )


# ----------------- PANEL VIEW -----------------

class SolarInfoPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="☀️ Fill Solar Details",
        style=discord.ButtonStyle.primary,
        custom_id="solarinfo:open_modal"
    )
    async def open_modal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild
        if not guild:
            return await safe_ephemeral(interaction, "❌ Server only.")

        panel_doc = solarinfo_col.find_one({"guild_id": guild.id})
        if not panel_doc:
            return await safe_ephemeral(interaction, "❌ Solar panel is not active in this server.")

        await interaction.response.send_modal(SolarInfoModal(panel_doc))


# ----------------- COG -----------------

class SolarInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(SolarInfoPanelView())

    @app_commands.command(
        name="solarinfo",
        description="Setup solar info panel in a selected channel"
    )
    @app_commands.describe(channel="Select the channel where the solar panel should be sent")
    @app_commands.guild_only()
    async def solarinfo(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only server owner or admin can use this command.")

        guild = interaction.guild
        existing = solarinfo_col.find_one({"guild_id": guild.id})
        if existing:
            return await safe_ephemeral(
                interaction,
                "⚠️ Solar info panel is already active in this server. Use `/solarinfooff` first."
            )

        panel_embed = _build_panel_embed()
        view = SolarInfoPanelView()

        msg = await channel.send(embed=panel_embed, view=view)

        solarinfo_col.insert_one({
            "guild_id": guild.id,
            "channel_id": channel.id,
            "message_id": msg.id,
            "created_at": datetime.now(timezone.utc)
        })

        await safe_ephemeral(
            interaction,
            f"✅ Solar info panel has been setup successfully in {channel.mention}."
        )

    @app_commands.command(
        name="solarinfooff",
        description="Delete the solar info panel and remove it from database"
    )
    @app_commands.guild_only()
    async def solarinfooff(self, interaction: discord.Interaction):
        if not is_admin_or_guild_owner(interaction):
            return await safe_ephemeral(interaction, "❌ Only server owner or admin can use this command.")

        guild = interaction.guild
        panel_doc = solarinfo_col.find_one({"guild_id": guild.id})

        if not panel_doc:
            return await safe_ephemeral(interaction, "❌ No active solar info panel found in this server.")

        try:
            channel = guild.get_channel(panel_doc["channel_id"])
            if channel is None:
                channel = await guild.fetch_channel(panel_doc["channel_id"])

            msg = await channel.fetch_message(panel_doc["message_id"])
            await msg.delete()
        except Exception:
            pass

        solarinfo_col.delete_one({"guild_id": guild.id})

        await safe_ephemeral(
            interaction,
            "🗑️ Solar info panel has been deleted and removed from the database."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SolarInfo(bot))