import os
import json
import discord
from discord.ext import commands

TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID"))

DATA_DIR = "data"
TICKET_FILE = f"{DATA_DIR}/ticket_panel.json"

# ===================== FILE HELPERS =====================

def load_ticket_message_id():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(TICKET_FILE):
        return None

    try:
        with open(TICKET_FILE, "r") as f:
            return json.load(f).get("message_id")
    except:
        return None

def save_ticket_message_id(message_id: int):
    with open(TICKET_FILE, "w") as f:
        json.dump({"message_id": message_id}, f)

# ===================== CLOSE BUTTON VIEW =====================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.secondary)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )

        if not (
            user == guild.owner
            or user.guild_permissions.administrator
            or channel.name == f"ticket-{user.id}"
        ):
            return await interaction.response.send_message(
                "❌ You are not allowed to close this ticket.",
                ephemeral=True
            )

        await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
        await channel.delete(reason="Ticket closed")

# ===================== CREATE BUTTON VIEW =====================

class TicketButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        for ch in guild.text_channels:
            if ch.name == f"ticket-{user.id}":
                return await interaction.response.send_message(
                    "❌ You already have an open ticket.",
                    ephemeral=True,
                    delete_after=4
                )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            overwrites=overwrites,
            reason="New ticket created"
        )

        embed = discord.Embed(
            description=(
                "Welcome to your ticket 👋\n\n"
                "Please explain your issue clearly.\n"
                "An admin will assist you shortly.\n\n"
                "Use the button below to close this ticket."
            ),
            color=discord.Color.blue()
        )

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention}",
            ephemeral=True,
            delete_after=4
        )

# ===================== COG =====================

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(TICKET_CHANNEL_ID)
        if not channel:
            return

        message_id = load_ticket_message_id()

        if message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(view=TicketButton(self.bot))
                return
            except:
                pass

        embed = discord.Embed(
            description=(
                "🎫 **Need Help?**\n\n"
                "Click the button below to create a ticket.\n"
                "Our team will help you shortly."
            ),
            color=discord.Color.green()
        )

        msg = await channel.send(embed=embed, view=TicketButton(self.bot))
        save_ticket_message_id(msg.id)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
