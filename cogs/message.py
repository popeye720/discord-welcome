import discord
from discord.ext import commands

class MessageImager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        # ---- FLAG CHECK ----
        ping_everyone = False
        if text.startswith("--ping"):
            ping_everyone = True
            text = text.replace("--ping", "", 1).strip()

        if not text:
            await ctx.send("❌ Message empty hai.")
            return

        embed = discord.Embed(
            description=text,
            color=discord.Color.blue()
        )

        files = []

        # 🖼️ IMAGE HANDLING (FIXED & STABLE)
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]

            if attachment.content_type and attachment.content_type.startswith("image"):
                file = await attachment.to_file()
                files.append(file)
                embed.set_image(url=f"attachment://{file.filename}")

        await channel.send(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            files=files if files else None,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
        )

        # ✅ CONFIRMATION (NO DELETE)
        await ctx.send(f"✅ Message sent to <#{channel_id}>")

    # ================= ERROR HANDLER =================

    @post.error
    async def post_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command!")

# ================= SETUP =================

async def setup(bot):
    await bot.add_cog(MessageImager(bot))
