import discord
from discord.ext import commands

ROLE_18 = 1438173585519935600
ROLE_MINOR = 1438173783717580840

EMOJI_18 = "🔞"
EMOJI_MINOR = "🧒"

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========= SETUP MESSAGE =========
    @commands.command()
    @commands.is_owner()
    async def rrsetup(self, ctx):
        embed = discord.Embed(
            title="Age Verification",
            description=(
                f"{EMOJI_18} → **18+**\n"
                f"{EMOJI_MINOR} → **Minor**"
            ),
            color=discord.Color.gold()
        )

        msg = await ctx.send(embed=embed)

        await msg.add_reaction(EMOJI_18)
        await msg.add_reaction(EMOJI_MINOR)

        await ctx.send(
            f"✅ Reaction role message created.\n"
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

        role_18 = guild.get_role(ROLE_18)
        role_minor = guild.get_role(ROLE_MINOR)

        if payload.emoji.name == EMOJI_18:
            if role_minor in member.roles:
                await member.remove_roles(role_minor)
            await member.add_roles(role_18)

        elif payload.emoji.name == EMOJI_MINOR:
            if role_18 in member.roles:
                await member.remove_roles(role_18)
            await member.add_roles(role_minor)

    # ========= REMOVE ROLE =========
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        role_18 = guild.get_role(ROLE_18)
        role_minor = guild.get_role(ROLE_MINOR)

        if payload.emoji.name == EMOJI_18:
            await member.remove_roles(role_18)

        elif payload.emoji.name == EMOJI_MINOR:
            await member.remove_roles(role_minor)

async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
