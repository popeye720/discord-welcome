import discord
from discord.ext import commands
import asyncio

# ================= AUTO DELETE (NON-AUTHORIZED USERS) =================

async def auto_delete_non_authorized(ctx, bot_text: str, delay: int = 3):
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

    # ---------- OWNER OR ADMIN CHECK ----------
    def has_permission(self, ctx):
        if not ctx.guild:
            return False
        return (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        )

    # ---------------- STREAM MODE ON ----------------
    @commands.command(name="streammode")
    async def streammode(self, ctx):
        if not self.has_permission(ctx):
            return await auto_delete_non_authorized(
                ctx,
                "You do not have permission to enable stream mode. "
                "Only the server owner or administrators are allowed.",
                delay=3
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("You must be connected to a voice channel to enable stream mode.")

        vc = ctx.author.voice.channel

        self.bot.blocked_voice_channel_id = vc.id
        self.bot.streammode_active = True

        # If the bot is already connected to the blocked channel, disconnect it
        if ctx.voice_client and ctx.voice_client.channel.id == vc.id:
            await ctx.voice_client.disconnect()

        await ctx.send(
            "Stream mode has been enabled.\n"
            f"The bot will not join the voice channel: {vc.name}"
        )

    # ---------------- STREAM MODE OFF ----------------
    @commands.command(name="streamoff")
    async def streamoff(self, ctx):
        if not self.has_permission(ctx):
            return await auto_delete_non_authorized(
                ctx,
                "You do not have permission to disable stream mode. "
                "Only the server owner or administrators are allowed.",
                delay=3
            )

        if not self.bot.streammode_active:
            return await ctx.send("Stream mode is currently not active.")

        self.bot.blocked_voice_channel_id = None
        self.bot.streammode_active = False

        await ctx.send(
            "Stream mode has been disabled. The bot can now join voice channels."
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
