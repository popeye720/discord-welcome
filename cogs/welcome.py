import os
import discord
from discord.ext import commands

WELCOME_CHANNEL = os.getenv("WELCOME_CHANNEL")
if not WELCOME_CHANNEL:
    raise RuntimeError("WELCOME_CHANNEL env variable not set")

WELCOME_CHANNEL_ID = int(WELCOME_CHANNEL)

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="👋 Welcome!",
            description=(
                f"{member.mention}, **Meet your new home! ❤️**\n\n"
                f"**MAKE SURE TO CHECK OUT:**\n"
                f"- <#1164407773174439986>\n"
                f"- <#1137328131024375858>\n"
            ),
            color=discord.Color.green()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1138497010345979944/1439314780681801829/dc.png"
        )

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
