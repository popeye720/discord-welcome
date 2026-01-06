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

    # -------- SET WELCOME (ONLY ONCE) --------
    @commands.command(name="setwelcome")
    @is_admin()
    async def set_welcome(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.reply("❌ Invalid channel ID")

        # ❌ already set check
        existing = greetings_col.find_one({
            "guild_id": ctx.guild.id
        })
        if existing:
            return await ctx.reply(
                "⚠️ Welcome is already set. Use `!delwelcome` first."
            )

        greetings_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel_id
        })

        await ctx.reply(f"✅ Welcome channel set to {channel.mention}")

    # -------- DELETE WELCOME --------
    @commands.command(name="delwelcome")
    @is_admin()
    async def delete_welcome(self, ctx):
        result = greetings_col.find_one_and_delete({
            "guild_id": ctx.guild.id
        })

        if not result:
            return await ctx.reply("❌ Welcome is not set.")

        await ctx.reply("✅ Welcome system deleted successfully.")

    # -------- TEST WELCOME --------
    @commands.command(name="testgreetings")
    @is_admin()
    async def test_greetings(self, ctx):
        data = greetings_col.find_one({
            "guild_id": ctx.guild.id
        })

        if not data:
            return await ctx.reply("❌ Welcome is not set.")

        channel = ctx.guild.get_channel(data["channel_id"])
        if not channel:
            return await ctx.reply("❌ Saved channel not found.")

        await channel.send(
            f"{ctx.author.mention} welcome to the server"
        )

    # -------- AUTO WELCOME ON JOIN --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = greetings_col.find_one({
            "guild_id": member.guild.id
        })

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
