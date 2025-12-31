import discord
from discord.ext import commands


class Embedder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔐 OWNER + ADMIN CHECK (AUTO)
    def can_manage(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    @commands.command(name="embedder")
    async def embedder(self, ctx, channel_id: int, image_url: str, *, message: str):
        # 🔒 Permission check
        if not self.can_manage(ctx):
            return await ctx.send(
                "You do not have permission to use this command."
            )

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid channel ID.")

        if not image_url.startswith("http"):
            return await ctx.send("Please provide a valid image URL.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # same image for thumbnail + main image
        embed.set_thumbnail(url=image_url)
        embed.set_image(url=image_url)

        # footer with author avatar only
        embed.set_footer(
            icon_url=ctx.author.display_avatar.url
        )

        await channel.send(embed=embed)
        await ctx.send(
            f"Embedded message sent to {channel.mention}"
        )


async def setup(bot):
    await bot.add_cog(Embedder(bot))
