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
        # ===== PUBLIC WELCOME (same as before) =====
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            rules_channel = "<#1164407773174439986>"
            chat_channel = "<#1137328131024375858>"

            embed = discord.Embed(
                description=(
                    "**MAKE SURE TO CHECK OUT:**\n"
                    f"📜・{rules_channel} → *Server Rules.*\n"
                    f"💬・{chat_channel} → *Start chatting from here.*"
                ),
                color=discord.Color.green()
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/1138497010345979944/1439314780681801829/dc.png"
            )

            await channel.send(
                content=f"{member.mention}, **Meet your new home! ❤️**",
                embed=embed
            )

        # ===== PERSONAL DM WELCOME =====
        try:
            dm_embed = discord.Embed(
                description=(
                    f"Hey {member.mention} 👋\n\n"
                    f"Welcome to **{member.guild.name}** ❤️\n\n"
                    "Thanks for joining our community!\n\n"
                    "**Please support our channels:**\n"
                    "▶️ **Nilesh YT**: https://www.youtube.com/@NILESHYT\n"
                    "▶️ **Nilesh Plays**: https://www.youtube.com/@Nileshplays12\n\n"
                    "Hope you enjoy your stay 🚀"
                ),
                color=discord.Color.blurple()
            )

            dm_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else member.display_avatar.url)

            await member.send(embed=dm_embed)
        except:
            pass  # agar user ke DMs closed ho

async def setup(bot):
    await bot.add_cog(Welcome(bot))








#needs to be tested