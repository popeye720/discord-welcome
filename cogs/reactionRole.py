import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/reaction_roles.json"

def load_data():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class ReactionRoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

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

        """
        Body format example:
        BOY - for boys 👦
        GIRL - for girls 👧
        """

        role_map = {}
        lines = body.splitlines()

        description_lines = []

        for line in lines:
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                return await ctx.send("Invalid format. Each line must end with an emoji.")

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

        guild_id = str(ctx.guild.id)
        self.data.setdefault(guild_id, {})
        self.data[guild_id][title] = {
            "channel_id": channel.id,
            "message_id": message.id,
            "roles": role_map
        }

        save_data(self.data)

        await ctx.send("Reaction role message created successfully.")

    # ---------- REMOVE REACTION ROLE ----------
    @commands.command(name="removerole")
    async def remove_role(self, ctx, channel_id: int, *, title: str):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        guild_id = str(ctx.guild.id)
        config = self.data.get(guild_id, {}).get(title)

        if not config:
            return await ctx.send("Reaction role with this title was not found.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid channel ID.")

        try:
            message = await channel.fetch_message(config["message_id"])
            await message.delete()
        except:
            pass

        del self.data[guild_id][title]
        save_data(self.data)

        await ctx.send("Reaction role message removed successfully.")

    # ---------- REACTION ADD ----------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        if not member:
            return

        guild_data = self.data.get(str(guild.id), {})
        for config in guild_data.values():
            if payload.message_id == config["message_id"]:
                role_name = config["roles"].get(payload.emoji.name)
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        await member.add_roles(role)

    # ---------- REACTION REMOVE ----------
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        if not member:
            return

        guild_data = self.data.get(str(guild.id), {})
        for config in guild_data.values():
            if payload.message_id == config["message_id"]:
                role_name = config["roles"].get(payload.emoji.name)
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRoleManager(bot))
