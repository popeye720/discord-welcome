import discord
from discord.ext import commands

from database.models import ticket_col
from database.mongo import db

# panel config collection
ticket_panel_col = db["ticket_panels"]


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
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.success,
        custom_id="ticket_create_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # 🔎 get panel config (ONLY ONE PER GUILD)
        panel = ticket_panel_col.find_one({
            "guild_id": guild.id
        })
        if not panel:
            return await interaction.response.send_message(
                "Ticket system is not configured on this server.",
                ephemeral=True
            )

        # ❌ same user duplicate ticket block
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
            else:
                ticket_col.delete_one({"_id": existing["_id"]})

        category = guild.get_channel(panel["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Ticket category is no longer available.",
                ephemeral=True
            )

        # 🔒 permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}".lower(),
            category=category,
            overwrites=overwrites,
            reason="User support ticket"
        )

        ticket_col.insert_one({
            "guild_id": guild.id,
            "user_id": user.id,
            "channel_id": ticket_channel.id,
            "open": True
        })

        embed = discord.Embed(
            title="Support Ticket",
            description="Please describe your issue and our team will assist you shortly.\nUse the **Close Ticket** button when resolved.",
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

    # -------- SETUP TICKET SYSTEM (ONLY ONCE PER SERVER) --------
    @commands.command(name="createticket")
    async def createticket(self, ctx, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel or not channel.category:
            return await ctx.send("❌ Invalid channel or missing category.")

        # ❌ block multiple setup per guild
        existing = ticket_panel_col.find_one({
            "guild_id": ctx.guild.id
        })
        if existing:
            return await ctx.send(
                "❌ Ticket system is already configured in this server."
            )

        ticket_panel_col.insert_one({
            "guild_id": ctx.guild.id,
            "panel_channel_id": channel.id,
            "category_id": channel.category.id
        })

        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Need assistance? Click the button below to create a ticket.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=TicketButton())

    # -------- DELETE TICKET SYSTEM --------
    @commands.command(name="deleteticket")
    async def deleteticket(self, ctx):
        panel = ticket_panel_col.find_one_and_delete({
            "guild_id": ctx.guild.id
        })

        if not panel:
            return await ctx.send("❌ Ticket system is not set up.")

        channel = self.bot.get_channel(panel["panel_channel_id"])
        if channel:
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user and msg.components:
                    await msg.delete()
                    break

        await ctx.send("✅ Ticket system deleted successfully.")


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
