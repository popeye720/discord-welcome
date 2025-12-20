import discord
from discord.ext import commands

class MessageImager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= POST =================

    @commands.command()
    @commands.is_owner()
    async def post(self, ctx, channel_id: int, *, text: str):

        if not text.strip():
            return await ctx.send("❌ Message empty hai.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID!")

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
            f"✅ Message sent | Channel: {channel.mention} | ID: `{msg.id}`"
        )

    # ================= POST EDIT =================

    @commands.command()
    @commands.is_owner()
    async def postedit(self, ctx, channel_id: int, message_id: int, *, new_text: str):

        if not new_text.strip():
            return await ctx.send("❌ Edit text empty hai.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID!")

        try:
            target_message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("❌ Message not found in that channel.")

        if target_message.author.id != self.bot.user.id:
            return await ctx.send("❌ I can only edit my own messages.")

        # Keep existing embed/image
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

        await ctx.send(f"✅ Message `{message_id}` edited successfully!")

    # ================= ERROR =================

    @post.error
    @postedit.error
    async def owner_only_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command!")

async def setup(bot):
    await bot.add_cog(MessageImager(bot))
