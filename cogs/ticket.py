import os
import discord
from discord.ext import commands

TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID"))

# ===================== CLOSE BUTTON VIEW =====================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.secondary  # YELLOW / GREY
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )

        # permission check
        is_owner = user == guild.owner
        is_admin = user.guild_permissions.administrator
        is_ticket_owner = channel.name == f"ticket-{user.id}"

        if not (is_owner or is_admin or is_ticket_owner):
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
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild
        user = interaction.user

        # check if user already has open ticket
        for channel in guild.text_channels:
            if channel.name == f"ticket-{user.id}":
                return await interaction.response.send_message(
                    "❌ You already have an open ticket.",
                    ephemeral=True
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

        # ---- EMBED (NO MENTION INSIDE) ----
        embed = discord.Embed(
            description=(
                "Welcome to your ticket 👋\n\n"
                "Please explain your issue clearly.\n"
                "An admin will assist you shortly.\n\n"
                "Use the button below to close this ticket."
            ),
            color=discord.Color.blue()
        )

        # ---- USER MENTION OUTSIDE EMBED (NOTIFICATION) ----
        await ticket_channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention}",
            ephemeral=True
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

        embed = discord.Embed(
            description=(
                "🎫 **Need Help?**\n\n"
                "Click the button below to create a ticket.\n"
                "Our team will help you shortly."
            ),
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=TicketButton(self.bot))


async def setup(bot):
    await bot.add_cog(Ticket(bot))
#cccc