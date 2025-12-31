import discord
from discord.ext import commands

class Embedder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔐 OWNER + ADMIN CHECK
    def can_manage(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    @commands.command(name="embedder")
    async def embedder(self, ctx, channel_id: int, *, message: str):
        # 🔒 Permission check
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid channel ID.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ Image OPTIONAL → if attached, use as thumbnail + image
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_thumbnail(url=attachment.url)
                embed.set_image(url=attachment.url)

        # footer with author avatar
        embed.set_footer(icon_url=ctx.author.display_avatar.url)

        await channel.send(embed=embed)
        await ctx.send(f"✅ Embedded message sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Embedder(bot))
