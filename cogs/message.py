import discord
from discord.ext import commands


class MessageImager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- OWNER OR ADMIN CHECK --------
    def has_permission(self, ctx):
        if not ctx.guild:
            return False
        return (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        )

    # ================= POST =================

    @commands.command()
    async def post(self, ctx, channel_id: int, *, text: str):
        if not self.has_permission(ctx):
            return await ctx.send(
                "You do not have permission to use this command. "
                "Only the server owner or administrators are allowed."
            )

        if not text.strip():
            return await ctx.send("Message content cannot be empty.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("The provided channel ID is invalid.")

        ping_everyone = False
        if text.startswith("--ping"):
            ping_everyone = True
            text = text.replace("--ping", "", 1).strip()

        embed = discord.Embed(
            description=text,
            color=discord.Color.blue()
        )

        files = []
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                file = await attachment.to_file()
                files.append(file)
                embed.set_image(url=f"attachment://{file.filename}")

        msg = await channel.send(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            files=files if files else None,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
        )

        await ctx.send(
            f"Message sent successfully.\n"
            f"Channel: {channel.mention}\n"
            f"Message ID: {msg.id}"
        )

    # ================= POST EDIT =================

    @commands.command()
    async def postedit(self, ctx, channel_id: int, message_id: int, *, new_text: str):
        if not self.has_permission(ctx):
            return await ctx.send(
                "You do not have permission to use this command. "
                "Only the server owner or administrators are allowed."
            )

        if not new_text.strip():
            return await ctx.send("Updated message content cannot be empty.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("The provided channel ID is invalid.")

        try:
            target_message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("The specified message could not be found.")

        if target_message.author.id != self.bot.user.id:
            return await ctx.send("Only messages sent by the bot can be edited.")

        embed = (
            target_message.embeds[0]
            if target_message.embeds
            else discord.Embed(color=discord.Color.blue())
        )

        embed.description = new_text
        embed.color = discord.Color.blue()

        await target_message.edit(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

        await ctx.send(f"Message with ID {message_id} has been updated successfully.")


async def setup(bot):
    await bot.add_cog(MessageImager(bot))
