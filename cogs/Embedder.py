import discord
from discord.ext import commands

class Embedder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 👑 owner auto-detect
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    @commands.command(name="embedder")
    async def embedder(self, ctx, channel_id: int, image_url: str, *, message: str):
        # 🔒 Owner-only
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **server owner** can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ SAME image for thumbnail + image
        if image_url.startswith("http"):
            embed.set_thumbnail(url=image_url)
            embed.set_image(url=image_url)
        else:
            return await ctx.send("❌ Please provide a valid image URL.")

        # 👤 Footer: only avatar icon
        embed.set_footer(icon_url=ctx.author.display_avatar.url)

        await channel.send(embed=embed)
        await ctx.send(f"✅ Embedded message sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Embedder(bot))
