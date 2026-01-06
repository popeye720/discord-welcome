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

    # ================= SEND EMBED =================
    @commands.command(name="embedder")
    async def embedder(self, ctx, channel_id: int, *, message: str):
        if not self.can_manage(ctx):
            return await ctx.send("❌ Only **Server Owner or Admin** can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        ping_everyone = False

        # 🔔 --ping flag
        if message.startswith("--ping"):
            if not ctx.author.guild_permissions.mention_everyone:
                return await ctx.send("❌ You don’t have permission to ping @everyone.")
            ping_everyone = True
            message = message.replace("--ping", "", 1).strip()

        if not message.strip():
            return await ctx.send("❌ Message content cannot be empty.")

        embed = discord.Embed(
            description=message,
            color=discord.Color.gold()
        )

        # 🖼️ Image attach (optional)
        if ctx.message.attachments:
            att = ctx.message.attachments[0]
            if att.content_type and att.content_type.startswith("image"):
                embed.set_image(url=att.url)

        embed.set_footer(
            text=f"Sent by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        msg = await channel.send(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
        )

        await ctx.send(
            f"✅ Embedded message sent.\n"
            f"Channel: {channel.mention}\n"
            f"Message ID: {msg.id}"
        )

    # ================= EDIT EMBED =================
    @commands.command(name="embededit")
    async def embed_edit(self, ctx, channel_id: int, message_id: int, *, new_message: str):
        if not self.can_manage(ctx):
            return await ctx.send("❌ Only **Server Owner or Admin** can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        try:
            target = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("❌ Message not found.")

        # ❌ only bot messages
        if target.author.id != self.bot.user.id:
            return await ctx.send("❌ Only bot messages can be edited.")

        ping_everyone = False

        # 🔔 --ping flag
        if new_message.startswith("--ping"):
            if not ctx.author.guild_permissions.mention_everyone:
                return await ctx.send("❌ You don’t have permission to ping @everyone.")
            ping_everyone = True
            new_message = new_message.replace("--ping", "", 1).strip()

        if not new_message.strip():
            return await ctx.send("❌ Message content cannot be empty.")

        # get existing embed or create new
        embed = (
            target.embeds[0]
            if target.embeds
            else discord.Embed(color=discord.Color.gold())
        )

        embed.description = new_message
        embed.color = discord.Color.gold()

        # 🖼️ Image handling
        if ctx.message.attachments:
            att = ctx.message.attachments[0]
            if att.content_type and att.content_type.startswith("image"):
                embed.set_image(url=att.url)
        # else → old image stays automatically

        embed.set_footer(
            text=f"Edited by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await target.edit(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
        )

        await ctx.send(f"✅ Embedded message `{message_id}` updated successfully.")


async def setup(bot):
    await bot.add_cog(Embedder(bot))
