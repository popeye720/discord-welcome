import discord
from discord.ext import commands

class DMAll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 👑 OWNER CHECK
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ------------------ SINGLE DM ------------------
    @commands.command(name="dm")
    async def dm_user(self, ctx, user: discord.User, *, message: str):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only **Server Owner** can use this command.")

        embed = discord.Embed(
            description=message,  # links clickable
            color=discord.Color.gold()
        )

        # 🖼️ ATTACHED IMAGE → thumbnail + niche image
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_thumbnail(url=attachment.url)  # 🔼 upar
                embed.set_image(url=attachment.url)      # 🔽 niche

        try:
            await user.send(embed=embed)
            await ctx.send(f"✅ DM sent to **{user}**")
        except discord.Forbidden:
            await ctx.send("❌ Cannot DM this user.")
        except Exception:
            await ctx.send("❌ Something went wrong.")

    # ------------------ DM ALL ------------------
    @commands.command(name="dmall")
    async def dm_all(self, ctx, *, message: str):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only **Server Owner** can use this command.")

        await ctx.send("📨 Sending embed DMs to all members...")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ ATTACHED IMAGE → thumbnail + niche image
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_thumbnail(url=attachment.url)  # 🔼 upar
                embed.set_image(url=attachment.url)      # 🔽 niche

        sent = 0
        failed = 0

        for member in ctx.guild.members:
            if member.bot:
                continue
            try:
                await member.send(embed=embed)
                sent += 1
            except:
                failed += 1

        await ctx.send(
            f"✅ **DM Completed**\n"
            f"📨 Sent: `{sent}` users\n"
            f"❌ Failed: `{failed}` users"
        )

async def setup(bot):
    await bot.add_cog(DMAll(bot))
