import discord
from discord.ext import commands

from database.models import ticket_col

# ---------------- CLOSE BUTTON ----------------

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_close_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        user = interaction.user

        data = ticket_col.find_one({"channel_id": channel.id})
        if not data:
            return await interaction.response.send_message(
                "This is not a ticket channel.",
                ephemeral=True
            )

        if not (
            user.guild_permissions.administrator
            or data["user_id"] == user.id
        ):
            return await interaction.response.send_message(
                "You cannot close this ticket.",
                ephemeral=True
            )

        await interaction.response.send_message("Closing ticket...", ephemeral=True)

        ticket_col.delete_one({"channel_id": channel.id})
        await channel.delete()

# ---------------- CREATE BUTTON ----------------

class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="ticket_create_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # 🔎 prevent duplicate ticket (DB based)
        existing = ticket_col.find_one({
            "guild_id": guild.id,
            "user_id": user.id,
            "open": True
        })
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(
                    f"You already have an open ticket: {ch.mention}",
                    ephemeral=True
                )

        # 📂 auto category
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites
        )

        # 💾 save to DB
        ticket_col.insert_one({
            "guild_id": guild.id,
            "user_id": user.id,
            "channel_id": ticket_channel.id,
            "open": True
        })

        embed = discord.Embed(
            description=(
                "Welcome to your ticket.\n\n"
                "Describe your issue here.\n"
                "Use the button below to close the ticket."
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

    # -------- CREATE PANEL --------
    @commands.command(name="createticket")
    async def createticket(self, ctx):
        await ctx.message.delete()

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description="Click the button below to create a ticket.",
            color=discord.Color.green()
        )

        await ctx.channel.send(
            embed=embed,
            view=TicketButton()
        )

    # -------- DELETE PANEL --------
    @commands.command(name="deleteticket")
    async def deleteticket(self, ctx):
        await ctx.message.delete()

        async for msg in ctx.channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.delete()
                break

# ---------------- SETUP ----------------

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    bot.add_view(TicketButton())
    bot.add_view(CloseTicketView())
