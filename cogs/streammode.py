import discord
from discord.ext import commands
import asyncio

# ================= AUTO DELETE (NON-OWNER) =================

async def auto_delete_non_owner(ctx, bot_text: str, delay: int = 3):
    try:
        bot_msg = await ctx.send(bot_text)
        await asyncio.sleep(delay)
        await ctx.message.delete()
        await bot_msg.delete()
    except:
        pass

# ================= STREAM MODE COG =================

class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.streammode_active = False
        self.bot.blocked_voice_channel_id = None

    # ---------- OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------------- STREAM MODE ON ----------------
    @commands.command(name="streammode")
    async def streammode(self, ctx):
        if not self.is_owner(ctx):
            return await auto_delete_non_owner(
                ctx,
                "Only the server owner can enable stream mode.",
                delay=3
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("You must be connected to a voice channel.")

        vc = ctx.author.voice.channel

        self.bot.blocked_voice_channel_id = vc.id
        self.bot.streammode_active = True

        # If this bot is already in the blocked channel, disconnect it
        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        await ctx.send(
            f"Stream mode enabled.\n"
            f"The bot will never join the voice channel: {vc.name}"
        )

    # ---------------- STREAM MODE OFF ----------------
    @commands.command(name="streamoff")
    async def streamoff(self, ctx):
        if not self.is_owner(ctx):
            return await auto_delete_non_owner(
                ctx,
                "Only the server owner can disable stream mode.",
                delay=3
            )

        if not self.bot.streammode_active:
            return await ctx.send("Stream mode is not active.")

        self.bot.blocked_voice_channel_id = None
        self.bot.streammode_active = False

        await ctx.send(
            "Stream mode disabled. The bot can now join voice channels."
        )

    # ---------------- BLOCK ALL BOTS FROM JOINING ----------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.bot.streammode_active:
            return

        if not member.bot:
            return

        if after.channel and after.channel.id == self.bot.blocked_voice_channel_id:
            try:
                await member.move_to(None)
            except:
                pass

async def setup(bot):
    await bot.add_cog(StreamMode(bot))
