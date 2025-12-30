import discord
from discord.ext import commands

from database.models import reactionrole_col


class ReactionRoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- SERVER OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------- ADD REACTION ROLE ----------
    @commands.command(name="addrole")
    async def add_role(self, ctx, channel_id: int, title: str, *, body: str):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid channel ID.")

        role_map = {}
        description_lines = []

        for line in body.splitlines():
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                return await ctx.send(
                    "Invalid format. Each line must end with an emoji."
                )

            text, emoji = parts
            role_name = text.split("-")[0].strip()

            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not role:
                return await ctx.send(f"Role not found: {role_name}")

            role_map[emoji] = role_name
            description_lines.append(f"{emoji} {text}")

        embed = discord.Embed(
            title=title,
            description="\n".join(description_lines),
            color=discord.Color.blue()
        )

        message = await channel.send(embed=embed)

        for emoji in role_map:
            await message.add_reaction(emoji)

        # 💾 SAVE TO DB
        reactionrole_col.insert_one({
            "guild_id": ctx.guild.id,
            "title": title,
            "channel_id": channel.id,
            "message_id": message.id,
            "roles": role_map
        })

        await ctx.send("✅ Reaction role message created successfully.")

    # ---------- REMOVE REACTION ROLE ----------
    @commands.command(name="removerole")
    async def remove_role(self, ctx, channel_id: int, *, title: str):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        data = reactionrole_col.find_one({
            "guild_id": ctx.guild.id,
            "title": title
        })

        if not data:
            return await ctx.send("Reaction role with this title was not found.")

        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(data["message_id"])
                await msg.delete()
            except Exception:
                pass

        reactionrole_col.delete_one({"_id": data["_id"]})

        await ctx.send("🗑️ Reaction role message removed successfully.")

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

        role_name = data["roles"].get(payload.emoji.name)
        if not role_name:
            return

        role = discord.utils.get(guild.roles, name=role_name)
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

        role_name = data["roles"].get(payload.emoji.name)
        if not role_name:
            return

        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.remove_roles(role)


async def setup(bot):
    await bot.add_cog(ReactionRoleManager(bot))
