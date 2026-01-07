import random
import discord
from discord.ext import commands
from database.models import fungames_col


class FunGames(commands.Cog):
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

    # -------- SET FUN GAMES CHANNEL --------
    @commands.command(name="fungames")
    @is_admin()
    async def set_fungames(self, ctx, channel_id: int):
        if fungames_col.find_one({"guild_id": ctx.guild.id}):
            return await ctx.reply("⚠️ Fun games already set.")

        channel = ctx.guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return await ctx.reply("❌ Invalid channel ID.")

        fungames_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel.id
        })

        await ctx.reply(f"✅ Fun games enabled in {channel.mention}")

    # -------- DELETE FUN GAMES --------
    @commands.command(name="delfungames")
    @is_admin()
    async def del_fungames(self, ctx):
        data = fungames_col.find_one_and_delete({
            "guild_id": ctx.guild.id
        })

        if not data:
            return await ctx.reply("❌ Fun games not set.")

        channel = ctx.guild.get_channel(data["channel_id"])
        if channel:
            await ctx.reply(
                f"✅ Fun games disabled for {channel.mention}"
            )
        else:
            await ctx.reply("✅ Fun games system deleted.")

    # -------- CHECK CHANNEL --------
    async def check_channel(self, ctx):
        data = fungames_col.find_one({"guild_id": ctx.guild.id})
        if not data:
            return False

        if ctx.channel.id != data["channel_id"]:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

            msg = await ctx.send(
                f"❌ {ctx.author.mention} use fun commands in <#{data['channel_id']}>"
            )
            await msg.delete(delay=3)
            return False

        return True

    # -------- COINFLIP --------
    @commands.command(name="coinflip")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def coinflip(self, ctx):
        if not await self.check_channel(ctx):
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        result = random.choice(["🪙 Heads", "🪙 Tails"])
        msg = await ctx.send(f"{ctx.author.mention} → **{result}**")
        await msg.delete(delay=5)

    # -------- DICE --------
    @commands.command(name="dice")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dice(self, ctx):
        if not await self.check_channel(ctx):
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        roll = random.randint(1, 6)
        msg = await ctx.send(
            f"🎲 {ctx.author.mention} rolled **{roll}**"
        )
        await msg.delete(delay=5)

    # -------- 8BALL --------
    @commands.command(name="8ball")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def eightball(self, ctx, *, question: str = None):
        if not await self.check_channel(ctx):
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if not question:
            msg = await ctx.send("❓ Ask a question!")
            return await msg.delete(delay=3)

        responses = [
            "Yes ✅",
            "No ❌",
            "Maybe 🤔",
            "Definitely ✔️",
            "I don't think so 😐",
            "Ask again later 🔮"
        ]

        msg = await ctx.send(
            f"🎱 **Question:** {question}\n"
            f"**Answer:** {random.choice(responses)}"
        )
        await msg.delete(delay=6)

    # -------- COOLDOWN HANDLER --------
    async def cooldown_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

            msg = await ctx.send(
                f"⏳ {ctx.author.mention} wait **{error.retry_after:.1f}s**"
            )
            await msg.delete(delay=3)

    coinflip.error = cooldown_error
    dice.error = cooldown_error
    eightball.error = cooldown_error


async def setup(bot):
    await bot.add_cog(FunGames(bot))
