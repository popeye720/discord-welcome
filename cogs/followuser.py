import os
import discord
from discord.ext import commands

OWNER_ID = int(os.getenv("OWNER_ID"))  # Loaded from Railway ENV

class FollowUser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.following = False
        self.primary_user_id = None
        self.secondary_user_id = None

    # 🔒 Owner check
    def is_owner(self, ctx):
        return ctx.author.id == OWNER_ID

    @commands.command(name="follow")
    async def follow(self, ctx, user1: discord.Member, user2: discord.Member = None):
        if not self.is_owner(ctx):
            return await ctx.reply("❌ This command can only be used by the bot owner.")

        self.following = True
        self.primary_user_id = user1.id
        self.secondary_user_id = user2.id if user2 else None

        message = (
            "✅ **Follow mode enabled**\n"
            f"👤 **Primary user:** {user1.mention}\n"
        )
        if user2:
            message += f"👤 **Secondary user:** {user2.mention}"

        await ctx.reply(message)
        await self.try_follow(ctx.guild)

    @commands.command(name="stopfollow")
    async def stopfollow(self, ctx):
        if not self.is_owner(ctx):
            return await ctx.reply("❌ This command can only be used by the bot owner.")

        self.following = False
        self.primary_user_id = None
        self.secondary_user_id = None

        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()

        await ctx.reply("🛑 **Follow mode has been disabled.**")

    async def try_follow(self, guild: discord.Guild):
        if not self.following:
            return

        target_member = None

        primary = guild.get_member(self.primary_user_id)
        secondary = guild.get_member(self.secondary_user_id) if self.secondary_user_id else None

        # Priority logic: primary > secondary
        if primary and primary.voice:
            target_member = primary
        elif secondary and secondary.voice:
            target_member = secondary

        if not target_member:
            if guild.voice_client:
                await guild.voice_client.disconnect()
            return

        channel = target_member.voice.channel
        voice_client = guild.voice_client

        if voice_client:
            if voice_client.channel != channel:
                await voice_client.move_to(channel)
        else:
            await channel.connect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.following:
            return

        if member.id not in (self.primary_user_id, self.secondary_user_id):
            return

        await self.try_follow(member.guild)


async def setup(bot):
    await bot.add_cog(FollowUser(bot))
