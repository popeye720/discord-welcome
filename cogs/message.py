import discord
from discord.ext import commands
import asyncio

class MessageImager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def post(self, ctx, channel_id: int, *, text: str):
        if not text.strip():
            msg = await ctx.send("❌ Message empty hai.")
            await asyncio.sleep(2)
            await msg.delete()
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            msg = await ctx.send("❌ Invalid channel ID!")
            await asyncio.sleep(2)
            await msg.delete()
            return

        # ---- FLAG CHECK ----
        ping_everyone = False
        if text.startswith("--ping"):
            ping_everyone = True
            text = text.replace("--ping", "", 1).strip()

        if not text:
            msg = await ctx.send("❌ Message empty hai.")
            await asyncio.sleep(2)
            await msg.delete()
            return

        embed = discord.Embed(
            description=text,
            color=discord.Color.blue()
        )

        # 🖼️ IMAGE HANDLING (NEW)
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]

            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)

        await channel.send(
            content="@everyone" if ping_everyone else None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=ping_everyone,
                roles=False,
                users=False
            )
        )

        confirm = await ctx.send(f"✅ Message sent to <#{channel_id}>")
        await asyncio.sleep(2)
        await confirm.delete()

        # delete command message safely
        try:
            await ctx.message.delete()
        except:
            pass

    # ================= ERROR HANDLER =================

    @post.error
    async def post_error(self, ctx, error):
        if getattr(ctx, "_owner_warned", False):
            return

        if isinstance(error, commands.NotOwner):
            ctx._owner_warned = True
            try:
                msg = await ctx.send("❌ Only the bot owner can use this command!")
                await asyncio.sleep(2)
                await msg.delete()
                await ctx.message.delete()
            except:
                pass

# ================= SETUP =================

async def setup(bot):
    await bot.add_cog(MessageImager(bot))
