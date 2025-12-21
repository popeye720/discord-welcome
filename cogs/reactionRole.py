import os
import discord
from discord.ext import commands

IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "").strip()

# ===== ROLES =====
ROLE_18 = 1438173585519935600
ROLE_MINOR = 1438173783717580840
ROLE_BOY = 1439319767902060789
ROLE_GIRL = 1439319577191252221

# ===== EMOJIS =====
EMOJI_18 = "🔞"
EMOJI_MINOR = "🧒"
EMOJI_BOY = "👦"
EMOJI_GIRL = "👧"

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========= SETUP MESSAGE =========
    @commands.command()
    @commands.is_owner()
    async def rrsetup(self, ctx, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        embed = discord.Embed(
            title="Role Selection",
            description=(
                f"**Age**\n"
                f"{EMOJI_18} → 18+\n"
                f"{EMOJI_MINOR} → Minor\n\n"
                f"**Gender**\n"
                f"{EMOJI_BOY} → Boy\n"
                f"{EMOJI_GIRL} → Girl"
            ),
            color=discord.Color.gold()
        )

        # 🖼️ Thumbnail + Image from ENV (safe)
        if IMAGE_URL.startswith("http"):
            embed.set_thumbnail(url=IMAGE_URL)
            embed.set_image(url=IMAGE_URL)

        msg = await channel.send(embed=embed)

        # Reactions
        await msg.add_reaction(EMOJI_18)
        await msg.add_reaction(EMOJI_MINOR)
        await msg.add_reaction(EMOJI_BOY)
        await msg.add_reaction(EMOJI_GIRL)

        await ctx.send(
            f"✅ Reaction role message sent to {channel.mention}\n"
            f"Message ID: `{msg.id}`"
        )

    # ========= ADD ROLE =========
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        r18 = guild.get_role(ROLE_18)
        rminor = guild.get_role(ROLE_MINOR)
        rboy = guild.get_role(ROLE_BOY)
        rgirl = guild.get_role(ROLE_GIRL)

        # ---- Age group ----
        if payload.emoji.name == EMOJI_18:
            await member.remove_roles(rminor)
            await member.add_roles(r18)

        elif payload.emoji.name == EMOJI_MINOR:
            await member.remove_roles(r18)
            await member.add_roles(rminor)

        # ---- Gender group ----
        elif payload.emoji.name == EMOJI_BOY:
            await member.remove_roles(rgirl)
            await member.add_roles(rboy)

        elif payload.emoji.name == EMOJI_GIRL:
            await member.remove_roles(rboy)
            await member.add_roles(rgirl)

    # ========= REMOVE ROLE =========
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        role_map = {
            EMOJI_18: ROLE_18,
            EMOJI_MINOR: ROLE_MINOR,
            EMOJI_BOY: ROLE_BOY,
            EMOJI_GIRL: ROLE_GIRL
        }

        role_id = role_map.get(payload.emoji.name)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
