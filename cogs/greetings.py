from discord.ext import commands
import discord

from database.models import greetings_col


class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- PERMISSION CHECK (ADMIN / OWNER) --------
    def is_admin():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.administrator
                or ctx.author.id == ctx.guild.owner_id
            )
        return commands.check(predicate)

    # -------- SET GREETINGS CHANNEL --------
    @commands.command(name="setgreetings")
    @is_admin()
    async def set_greetings(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID")

        greetings_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"channel_id": channel_id}},
            upsert=True
        )

        await ctx.reply(f"✅ Greetings channel set to {channel.mention}")

    # -------- TEST GREETINGS --------
    @commands.command(name="testgreetings")
    @is_admin()
    async def test_greetings(self, ctx):
        data = greetings_col.find_one(
            {"guild_id": ctx.guild.id}
        )

        if not data:
            return await ctx.reply("❌ Greetings channel not set")

        channel = ctx.guild.get_channel(data["channel_id"])
        if not channel:
            return await ctx.reply("❌ Saved channel not found")

        await channel.send(
            f"{ctx.author.mention} welcome to the server"
        )

    # -------- AUTO WELCOME ON JOIN --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = greetings_col.find_one(
            {"guild_id": member.guild.id}
        )

        if not data:
            return

        channel = member.guild.get_channel(data["channel_id"])
        if not channel:
            return

        await channel.send(
            f"{member.mention} welcome to the server"
        )


async def setup(bot):
    await bot.add_cog(Greetings(bot))
