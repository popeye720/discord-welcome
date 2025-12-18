import os
import discord
from discord.ext import commands

TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID"))

class TicketButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # check if user already has open ticket
        for channel in guild.text_channels:
            if channel.name == f"ticket-{user.id}":
                await interaction.response.send_message(
                    "❌ You already have an open ticket.", ephemeral=True
                )
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            overwrites=overwrites,
            reason="New ticket created"
        )

        embed = discord.Embed(
            description=(
                f"Hello {user.mention} 👋\n\n"
                "Please explain your issue clearly.\n"
                "An admin will assist you shortly.\n\n"
                "To close this ticket, type:\n"
                "`!closeticket`"
            ),
            color=discord.Color.blue()
        )

        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True
        )


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(TICKET_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                description=(
                    "🎫 **Need Help?**\n\n"
                    "Click the button below to create a ticket.\n"
                    "Our team will help you shortly."
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed, view=TicketButton(self.bot))

    @commands.command()
    async def closeticket(self, ctx):
        if not ctx.channel.name.startswith("ticket-"):
            return

        # permission check: user / admin / owner
        is_owner = ctx.author == ctx.guild.owner
        is_admin = ctx.author.guild_permissions.administrator
        is_ticket_owner = ctx.channel.name == f"ticket-{ctx.author.id}"

        if not (is_owner or is_admin or is_ticket_owner):
            return

        await ctx.send("🔒 Closing ticket...")
        await ctx.channel.delete(reason="Ticket closed")


async def setup(bot):
    await bot.add_cog(Ticket(bot))
