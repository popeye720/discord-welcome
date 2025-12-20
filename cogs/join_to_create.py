import discord
from discord.ext import commands
import os

JOIN_TO_CREATE_CHANNEL_ID = int(os.getenv("JOIN_TO_CREATE_CHANNEL_ID"))

class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # user_id : channel_id

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        # User joined Join-to-Create channel
        if after.channel and after.channel.id == JOIN_TO_CREATE_CHANNEL_ID:
            guild = member.guild
            category = after.channel.category

            channel_name = f"{member.name}'s VC"

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True, manage_channels=True)
            }

            new_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )

            await member.move_to(new_channel)
            self.temp_channels[member.id] = new_channel.id

        # User left a temp channel → delete if empty
        if before.channel:
            channel = before.channel

            if (
                channel.id in self.temp_channels.values()
                and len(channel.members) == 0
            ):
                await channel.delete()

                # cleanup dict
                for user_id, ch_id in list(self.temp_channels.items()):
                    if ch_id == channel.id:
                        del self.temp_channels[user_id]
