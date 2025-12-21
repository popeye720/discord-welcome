import discord
from discord.ext import commands
import os

JOIN_TO_CREATE_CHANNEL_ID = int(os.getenv("JOIN_TO_CREATE_CHANNEL_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))

class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = set()  # store temporary VC ids

    # ================= LISTENER =================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        # 🟢 User joined Join-to-Create channel
        if after.channel and after.channel.id == JOIN_TO_CREATE_CHANNEL_ID:
            guild = member.guild
            category = after.channel.category

            channel_name = f"{member.name}'s VC"

            # 🔒 Private VC permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    connect=False,
                    speak=False
                ),
                member: discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    manage_channels=True,
                    move_members=True
                )
            }

            new_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )

            await member.move_to(new_channel)
            self.temp_channels.add(new_channel.id)

        # 🔴 Delete empty temporary channels
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                await before.channel.delete()
                self.temp_channels.remove(before.channel.id)

    # ================= VC ALLOW =================

    @commands.command(name="vcallow")
    async def vc_allow(self, ctx, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.send("❌ You are not connected to a voice channel.")

        vc = ctx.author.voice.channel

        if vc.id not in self.temp_channels:
            return await ctx.send("❌ This is not a temporary voice channel.")

        await vc.set_permissions(
            member,
            connect=True,
            speak=True
        )

        await ctx.send(f"✅ **{member.mention}** has been granted VC access.")

    # ================= VC REMOVE =================

    @commands.command(name="vcremove")
    async def vc_remove(self, ctx, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.send("❌ You are not connected to a voice channel.")

        vc = ctx.author.voice.channel

        if vc.id not in self.temp_channels:
            return await ctx.send("❌ This is not a temporary voice channel.")

        # 🚫 Do not remove owner
        if member.id == OWNER_ID:
            return await ctx.send("❌ You cannot remove the server owner from the voice channel.")

        # ❌ Remove permissions
        await vc.set_permissions(member, overwrite=None)

        # 🔄 Disconnect user if inside VC
        if member.voice and member.voice.channel == vc:
            await member.move_to(None)

        await ctx.send(f"🚫 **{member.mention}** has been removed from the voice channel.")

# 🔥 REQUIRED FOR load_extension
async def setup(bot):
    await bot.add_cog(JoinToCreate(bot))
