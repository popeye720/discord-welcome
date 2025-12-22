import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

class DMAll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------ SINGLE DM ------------------
    @commands.command(name="dm")
    async def dm_user(self, ctx, user: discord.User, *, message: str):
        # Owner only
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        try:
            await user.send(message)
            await ctx.send(f"✅ DM sent to **{user}**")
        except discord.Forbidden:
            await ctx.send("❌ Cannot DM this user.")
        except Exception:
            await ctx.send("❌ Something went wrong.")

    # ------------------ DM ALL ------------------
    @commands.command(name="dmall")
    async def dm_all(self, ctx, *, message: str):
        # Owner only
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Only the bot owner can use this command.")

        await ctx.send("📨 Sending DMs to all members...")

        sent = 0
        failed = 0

        for member in ctx.guild.members:
            if member.bot:
                continue

            try:
                await member.send(message)
                sent += 1
            except discord.Forbidden:
                failed += 1
            except Exception:
                failed += 1

        await ctx.send(
            f"✅ **DM Completed**\n"
            f"📨 Sent: `{sent}` users\n"
            f"❌ Failed: `{failed}` users"
        )

async def setup(bot):
    await bot.add_cog(DMAll(bot))
