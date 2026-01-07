import discord
from discord.ext import commands
import time


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- ADMIN / OWNER CHECK --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- PING COMMAND --------
    @commands.command(name="ping")
    @is_admin()
    async def ping(self, ctx):
        # Websocket latency
        ws_latency = round(self.bot.latency * 1000)

        # Message latency
        start = time.perf_counter()
        msg = await ctx.send("🏓 Checking ping...")
        end = time.perf_counter()

        msg_latency = round((end - start) * 1000)

        embed = discord.Embed(
            title="🏓 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 Bot Status",
            value="Online",
            inline=False
        )

        embed.add_field(
            name="📶 WebSocket Latency",
            value=f"`{ws_latency} ms`",
            inline=True
        )

        embed.add_field(
            name="⏱ Message Latency",
            value=f"`{msg_latency} ms`",
            inline=True
        )

        embed.set_footer(text="Bot is running smoothly 🚀")

        await msg.edit(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(Ping(bot))
