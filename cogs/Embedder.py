import discord
from discord.ext import commands

class Embedder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 👑 OWNER + ADMIN CHECK
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
        # 🔒 Owner / Admin only
        if not self.can_manage(ctx):
            return await ctx.send("❌ Only **Server Owner or Admin** can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        ping_everyone = False

        # 🔔 --ping flag check
        if message.startswith("--ping"):
            # 🔐 Mention Everyone permission check
            if not ctx.author.guild_permissions.mention_everyone:
                return await ctx.send("❌ You don’t have permission to ping @everyone.")

            ping_everyone = True
            message = message.replace("--ping", "", 1).strip()

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ Image OPTIONAL → thumbnail + image
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_thumbnail(url=attachment.url)
                embed.set_image(url=attachment.url)

        # footer
        embed.set_footer(icon_url=ctx.author.display_avatar.url)

        # 📣 Send embed
        content = "@everyone" if ping_everyone else None
        await channel.send(content=content, embed=embed)

        await ctx.send(f"✅ Embedded message sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Embedder(bot))
