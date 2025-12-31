import discord
from discord.ext import commands


class JoinLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- PERMISSION CHECK (OWNER + ADMIN) --------
    async def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            return False

        if (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return True

        await ctx.send(
            "You do not have permission to use this command."
        )
        return False

    # -------- JOIN VOICE CHANNEL --------
    @commands.command(name="joinvc")
    async def joinvc(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            return await ctx.send(
                "Invalid voice channel ID."
            )

        if ctx.guild.voice_client:
            await ctx.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        await ctx.send(
            f"Joined voice channel: {channel.name}"
        )

    # -------- LEAVE VOICE CHANNEL --------
    @commands.command(name="leavevc")
    async def leavevc(self, ctx):
        vc = ctx.guild.voice_client

        if not vc:
            return await ctx.send(
                "The bot is not connected to any voice channel."
            )

        await vc.disconnect()
        await ctx.send(
            "Disconnected from the voice channel."
        )


async def setup(bot):
    await bot.add_cog(JoinLeave(bot))
