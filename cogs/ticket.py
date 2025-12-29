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

        await interaction.response.send_message("Closing ticket...", ephemeral=True)
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
                "Ticket category missing.",
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
            overwrites=overwrites
        )

        embed = discord.Embed(
            description=(
                "Welcome to your ticket.\n\n"
                "Please describe your issue clearly.\n"
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

    # ---------- SET CATEGORY (ONCE) ----------
    @commands.command(name="setticket")
    async def setticket(self, ctx, category_id: int):
        if not self.is_owner(ctx):
            await ctx.message.delete()
            return

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            await ctx.message.delete()
            return

        self.data[str(ctx.guild.id)] = {
            "category_id": category.id
        }
        save_data(self.data)

        await ctx.message.delete()

    # ---------- CREATE PANEL ----------
    @commands.command(name="createticket")
    async def createticket(self, ctx):
        if not self.is_owner(ctx):
            await ctx.message.delete()
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in self.data:
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                "Need help?\n\n"
                "Click the button below to create a ticket."
            ),
            color=discord.Color.green()
        )

        panel_msg = await ctx.channel.send(
            embed=embed,
            view=TicketButton(self.bot)
        )

        self.data[guild_id]["panel_channel_id"] = ctx.channel.id
        self.data[guild_id]["panel_message_id"] = panel_msg.id
        save_data(self.data)

        await ctx.message.delete()

    # ---------- DELETE PANEL ----------
    @commands.command(name="deleteticket")
    async def deleteticket(self, ctx):
        if not self.is_owner(ctx):
            await ctx.message.delete()
            return

        guild_id = str(ctx.guild.id)
        config = self.data.get(guild_id)
        if not config:
            await ctx.message.delete()
            return

        if config.get("panel_channel_id") != ctx.channel.id:
            await ctx.message.delete()
            return

        try:
            channel = ctx.guild.get_channel(config["panel_channel_id"])
            msg = await channel.fetch_message(config["panel_message_id"])
            await msg.delete()
        except:
            pass

        config.pop("panel_channel_id", None)
        config.pop("panel_message_id", None)
        save_data(self.data)

        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    bot.add_view(TicketButton(bot))
    bot.add_view(CloseTicketView())
