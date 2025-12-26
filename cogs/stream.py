import discord
from discord.ext import commands
import os
import asyncio

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ================= AUTO DELETE (ONLY X USER) =================

async def auto_delete_xuser(ctx, bot_text: str, delay: int = 3):
    try:
        bot_msg = await ctx.send(bot_text)

        # 👑 OWNER SAFE
        if ctx.author.id == OWNER_ID:
            return

        await asyncio.sleep(delay)
        await ctx.message.delete()
        await bot_msg.delete()
    except:
        pass


# ================= STREAM MODE COG =================

class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 🔎 track stream mode state
        self.bot.streammode_active = False

    @commands.command(name="streammode")
    async def streammode(self, ctx):

        # ❌ X USER
        if ctx.author.id != OWNER_ID:
            return await auto_delete_xuser(
                ctx,
                "❌ Only owner can enable stream mode.",
                delay=3
            )

        # 👑 OWNER
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Join a voice channel first.")

        vc = ctx.author.voice.channel
        self.bot.blocked_voice_channel_id = vc.id
        self.bot.streammode_active = True   # ✅ ACTIVE

        # bot already VC me ho to leave
        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        await ctx.send(
            f"🔒 **Stream Mode ON**\nBot will never join **{vc.name}**"
        )

    @commands.command(name="streamoff")
    async def streamoff(self, ctx):

        # ❌ X USER
        if ctx.author.id != OWNER_ID:
            return await auto_delete_xuser(
                ctx,
                "❌ Only owner can disable stream mode.",
                delay=3
            )

        # ❗ STREAM MODE ACTIVE HI NAHI
        if not getattr(self.bot, "streammode_active", False):
            return await ctx.send(
                "⚠️ Stream Mode is **not active**."
            )

        # 👑 OWNER — TURN OFF
        self.bot.blocked_voice_channel_id = None
        self.bot.streammode_active = False  # ❌ INACTIVE

        await ctx.send(
            "🔓 **Stream Mode OFF** — bot can join voice channels now."
        )


async def setup(bot):
    await bot.add_cog(StreamMode(bot))
