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
            await ctx.send("❌ Message empty hai.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Invalid channel ID!")
            return

        ping_everyone = False
        if text.startswith("--ping"):
            ping_everyone = True
            text = text.replace("--ping", "", 1).strip()

        embed = discord.Embed(description=text, color=discord.Color.blue())

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

        await ctx.send(f"✅ Message sent | Channel: {channel.mention} | ID: `{msg.id}`")

    # ================= POST EDIT (FIXED) =================

    @commands.command()
    @commands.is_owner()
    async def postedit(self, ctx, channel_id: int, message_id: int, *, new_text: str):

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Invalid channel ID!")
            return

        ping_everyone = False
        if new_text.startswith("--ping"):
            ping_everyone = True
            new_text = new_text.replace("--ping", "", 1).strip()

        if not new_text:
            await ctx.send("❌ Edit text empty hai.")
            return

        try:
            target_message = await channel.fetch_message(message_id)
        except:
            await ctx.send("❌ Message not found in that channel.")
            return

        if target_message.author.id != self.bot.user.id:
            await ctx.send("❌ I can only edit my own messages.")
            return

        embed = target_message.embeds[0] if target_message.embeds else discord.Embed()
        embed.description = new_text
        embed.color = discord.Color.blue()

        files = []
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                file = await attachment.to_file()
                files.append(file)
                embed.set_image(url=f"attachment://{file.filename}")

        await target_message.edit(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            attachments=[],
            files=files if files else None,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
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
