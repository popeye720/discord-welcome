import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/ticket.json"

# ---------------- DATA HELPERS ----------------

def load_data():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---------------- CLOSE BUTTON ----------------

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.secondary)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                "This is not a ticket channel.",
                ephemeral=True
            )

        if not (
            user.id == guild.owner_id
            or user.guild_permissions.administrator
            or channel.name == f"ticket-{user.id}"
        ):
            return await interaction.response.send_message(
                "You are not allowed to close this ticket.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "Closing ticket...",
            ephemeral=True
        )
        await channel.delete(reason="Ticket closed")

# ---------------- CREATE BUTTON ----------------

class TicketButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.data = load_data()

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        guild_id = str(guild.id)

        config = self.data.get(guild_id)
        if not config:
            return await interaction.response.send_message(
                "Ticket system is not configured.",
                ephemeral=True
            )

        category = guild.get_channel(config["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Ticket category is missing.",
                ephemeral=True
            )

        for ch in category.text_channels:
            if ch.name == f"ticket-{user.id}":
                return await interaction.response.send_message(
                    "You already have an open ticket.",
                    ephemeral=True
                )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites,
            reason="New ticket created"
        )

        embed = discord.Embed(
            description=(
                "Welcome to your ticket.\n\n"
                "Please describe your issue clearly.\n"
                "A staff member will assist you shortly.\n\n"
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
            f"Ticket created: {ticket_channel.mention}",
            ephemeral=True
        )

# ---------------- COG ----------------

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ---------- OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------- SET TICKET ----------
    @commands.command(name="setticket")
    async def set_ticket(self, ctx, category_id: int):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.send("Invalid category ID.")

        guild_id = str(ctx.guild.id)

        self.data[guild_id] = {
            "category_id": category.id,
            "panel_channel_id": ctx.channel.id
        }
        save_data(self.data)

        embed = discord.Embed(
            description=(
                "Need help?\n\n"
                "Click the button below to create a ticket.\n"
                "Our team will assist you shortly."
            ),
            color=discord.Color.green()
        )

        await ctx.channel.send(
            embed=embed,
            view=TicketButton(self.bot)
        )

        await ctx.send("Ticket system has been set up successfully.")

    # ---------- DELETE TICKET ----------
    @commands.command(name="deleteticket")
    async def delete_ticket(self, ctx):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        guild_id = str(ctx.guild.id)

        if guild_id not in self.data:
            return await ctx.send("Ticket system is not set up for this server.")

        del self.data[guild_id]
        save_data(self.data)

        await ctx.send("Ticket system has been deleted successfully.")

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
