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

        # -------- EMBED HELP MESSAGE --------
        embed = discord.Embed(
            title="🎮 Fun Games",
            description="Play simple fun games using the commands below!",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🪙 !coinflip",
            value="Flip a coin and get **Heads** or **Tails**.",
            inline=False
        )
        embed.add_field(
            name="🎲 !dice",
            value="Roll a dice and get a number from **1 to 6**.",
            inline=False
        )
        embed.add_field(
            name="🎱 !8ball <question>",
            value="Ask a yes/no question and get a fun answer.",
            inline=False
        )

        embed.set_footer(text="Have fun 😄")

        help_msg = await channel.send(embed=embed)

        # -------- SAVE TO DB --------
        fungames_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel.id,
            "message_id": help_msg.id
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
            try:
                msg = await channel.fetch_message(data["message_id"])
                await msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

            await ctx.reply(f"✅ Fun games disabled for {channel.mention}")
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
        await ctx.send(
            f"{ctx.author.mention} → **{random.choice(['🪙 Heads', '🪙 Tails'])}**"
        )

    # -------- DICE --------
    @commands.command(name="dice")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dice(self, ctx):
        if not await self.check_channel(ctx):
            return
        await ctx.send(
            f"🎲 {ctx.author.mention} rolled **{random.randint(1, 6)}**"
        )

    # -------- 8BALL --------
    @commands.command(name="8ball")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def eightball(self, ctx, *, question: str = None):
        if not await self.check_channel(ctx):
            return

        if not question:
            msg = await ctx.send("❓ Ask a question!")
            return await msg.delete(delay=3)

        responses = [
            "Yes ✅", "No ❌", "Maybe 🤔",
            "Definitely ✔️", "Ask again later 🔮"
        ]

        await ctx.send(
            f"🎱 **Question:** {question}\n"
            f"**Answer:** {random.choice(responses)}"
        )

    # -------- COOLDOWN HANDLER --------
    async def cooldown_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = await ctx.send(
                f"⏳ {ctx.author.mention} wait **{error.retry_after:.1f}s**"
            )
            await msg.delete(delay=3)

    coinflip.error = cooldown_error
    dice.error = cooldown_error
    eightball.error = cooldown_error


async def setup(bot):
    await bot.add_cog(FunGames(bot))
