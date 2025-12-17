import discord
from discord.ext import commands
import asyncio
import os

class MessageImager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = int(os.getenv("OWNER_ID"))

    @commands.command()
    async def post(self, ctx, channel_id: int, *, text: str):
        # Owner check
        if ctx.author.id != self.owner_id:
            warning = await ctx.send("❌ Only the bot owner can use this command!")
            await asyncio.sleep(2)
            try:
                await ctx.message.delete()
                await warning.delete()
            except:
                pass
            return

        if not text.strip():
            return await ctx.send("❌ Message empty hai.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            msg = await ctx.send("❌ Invalid channel ID!")
            await asyncio.sleep(2)
            try:
                await ctx.message.delete()
                await msg.delete()
            except:
                pass
            return

        embed = discord.Embed(
            description=text,
            color=discord.Color.blue()
        )

        # IMPORTANT: allow mentions only if user typed them
        await channel.send(
            content=text,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                roles=True,
                users=True
            )
        )

        await ctx.send(f"✅ Message sent to <#{channel_id}>")

async def setup(bot):
    await bot.add_cog(MessageImager(bot))
