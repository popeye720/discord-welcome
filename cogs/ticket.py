import discord
from discord.ext import commands

from database.models import ticket_col


# ================= CLOSE BUTTON =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        user = interaction.user

        data = ticket_col.find_one({"channel_id": channel.id})
        if not data:
            return await interaction.response.send_message(
                "This channel is not associated with a ticket.",
                ephemeral=True
            )

        if not (user.guild_permissions.administrator or data["user_id"] == user.id):
            return await interaction.response.send_message(
                "You do not have permission to close this ticket.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "This ticket will now be closed.",
            ephemeral=True
        )

        ticket_col.delete_one({"channel_id": channel.id})
        await channel.delete()


# ================= CREATE BUTTON =================

class TicketButton(discord.ui.View):
    def __init__(self, category_id: int):
        super().__init__(timeout=None)
        self.category_id = category_id

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.success,
        custom_id="ticket_create_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Prevent duplicate ticket
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

        category = guild.get_channel(self.category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Ticket category is no longer available.",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}".lower(),
            category=category,
            overwrites=overwrites
        )

        ticket_col.insert_one({
            "guild_id": guild.id,
            "user_id": user.id,
            "channel_id": ticket_channel.id,
            "open": True
        })

        embed = discord.Embed(
            title="Support Ticket",
            description=(
                "Thank you for reaching out to our support team.\n\n"
                "Please describe your issue clearly, and a staff member "
                "will assist you as soon as possible.\n\n"
                "Use the **Close Ticket** button below once your issue is resolved."
            ),
            color=discord.Color.blurple()
        )

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )


# ================= COG =================

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- CREATE PANEL --------
    @commands.command(name="createticket")
    async def createticket(self, ctx, channel_id: int):
        await ctx.message.delete()

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.", delete_after=5)

        if not channel.category:
            return await ctx.send(
                "❌ This channel is not under any category.",
                delete_after=5
            )

        embed = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "If you need assistance, please create a ticket.\n\n"
                "Our team will respond as soon as possible."
            ),
            color=discord.Color.green()
        )

        await channel.send(
            embed=embed,
            view=TicketButton(channel.category.id)
        )

    # -------- DELETE PANEL --------
    @commands.command(name="deleteticket")
    async def deleteticket(self, ctx, channel_id: int):
        await ctx.message.delete()

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.delete()
                break


# ================= SETUP =================

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    bot.add_view(CloseTicketView())
