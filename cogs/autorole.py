import os
import discord
from discord.ext import commands

ROLE_ID = os.getenv("AUTO_ROLE_ID")
if not ROLE_ID:
    raise RuntimeError("AUTO_ROLE_ID env variable not set")

ROLE_ID = int(ROLE_ID)

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = member.guild.get_role(ROLE_ID)
        if not role:
            return

        try:
            await member.add_roles(role, reason="Auto role on join")
        except:
            pass

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
