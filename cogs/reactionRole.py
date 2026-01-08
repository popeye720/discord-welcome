import discord
from discord.ext import commands
import re
from database.models import reactionrole_col

ROLE_MENTION_REGEX = re.compile(r"<@&(\d+)>")

class ReactionRoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------- ADD REACTION ROLE ----------
    @commands.command(name="addrole")
    @commands.guild_only()
    async def add_role(self, ctx, channel_id: int, title: str, *, body: str):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **Server Owner** can use this command.")

        # block duplicate title
        if reactionrole_col.find_one({"guild_id": ctx.guild.id, "title": title}):
            return await ctx.send("❌ Reaction role with this title already exists.")

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("❌ Invalid channel ID.")

        role_map = {}
        description_lines = []

        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue

            # split emoji (last part)
            try:
                text, emoji = line.rsplit(" ", 1)
            except ValueError:
                return await ctx.send(
                    "❌ Each line must end with an emoji."
                )

            # extract role mention
            match = ROLE_MENTION_REGEX.search(text)
            if not match:
                return await ctx.send(
                    f"❌ Invalid role mention format:\n`{line}`"
                )

            role_id = int(match.group(1))
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send(
                    f"❌ Role not found for ID `{role_id}`"
                )

            role_map[str(emoji)] = role.id
            description_lines.append(f"{emoji} {text}")

        if not role_map:
            return await ctx.send("❌ No valid roles found.")

        embed = discord.Embed(
            title=title,
            description="\n".join(description_lines),
            color=discord.Color.blue()
        )

        message = await channel.send(embed=embed)

        for emoji in role_map:
            try:
                await message.add_reaction(emoji)
            except:
                pass

        reactionrole_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": channel.id,
            "message_id": message.id,
            "title": title,
            "roles": role_map
        })

        await ctx.send("✅ Reaction role message created successfully.")

    # ---------- REMOVE REACTION ROLE ----------
    @commands.command(name="removerole")
    @commands.guild_only()
    async def remove_role(self, ctx, *, title: str):
        if not self.is_owner(ctx):
            return await ctx.send("❌ Only the **Server Owner** can use this command.")

        data = reactionrole_col.find_one_and_delete({
            "guild_id": ctx.guild.id,
            "title": title
        })

        if not data:
            return await ctx.send("❌ Reaction role not found.")

        channel = ctx.guild.get_channel(data["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(data["message_id"])
                await msg.delete()
            except:
                pass

        await ctx.send("🗑️ Reaction role removed successfully.")

    # ---------- REACTION ADD ----------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        data = reactionrole_col.find_one({
            "guild_id": payload.guild_id,
            "message_id": payload.message_id
        })
        if not data:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        role_id = data["roles"].get(str(payload.emoji))
        if not role_id:
            return

        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)

    # ---------- REACTION REMOVE ----------
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        data = reactionrole_col.find_one({
            "guild_id": payload.guild_id,
            "message_id": payload.message_id
        })
        if not data:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        role_id = data["roles"].get(str(payload.emoji))
        if not role_id:
            return

        role = guild.get_role(role_id)
        if role:
            await member.remove_roles(role)


async def setup(bot):
    await bot.add_cog(ReactionRoleManager(bot))
