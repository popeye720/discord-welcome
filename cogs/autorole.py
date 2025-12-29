import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/autorole.json"

# ---------------- DATA HELPERS ----------------

def load_data():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---------------- COG ----------------

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ---------- OWNER CHECK ----------
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ---------- MEMBER JOIN ----------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)
        role_ids = self.data.get(guild_id, [])

        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto role on join")
                except:
                    pass

    # ---------- ADD AUTOROLE ----------
    @commands.command(name="autorole")
    async def add_autorole(self, ctx, role_id: int):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send("Invalid role ID.")

        guild_id = str(ctx.guild.id)
        roles = self.data.get(guild_id, [])

        if role_id in roles:
            return await ctx.send("This role is already in the auto-role list.")

        roles.append(role_id)
        self.data[guild_id] = roles
        save_data(self.data)

        await ctx.send(f"Auto role added: {role.name}")

    # ---------- REMOVE AUTOROLE ----------
    @commands.command(name="removeautorole")
    async def remove_autorole(self, ctx, role_id: int):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        guild_id = str(ctx.guild.id)
        roles = self.data.get(guild_id, [])

        if role_id not in roles:
            return await ctx.send("This role is not in the auto-role list.")

        roles.remove(role_id)

        if roles:
            self.data[guild_id] = roles
        else:
            self.data.pop(guild_id, None)

        save_data(self.data)

        role = ctx.guild.get_role(role_id)
        await ctx.send(f"Auto role removed: {role.name if role else role_id}")

    # ---------- CLEAR ALL ----------
    @commands.command(name="clearautoroles")
    async def clear_autoroles(self, ctx):
        if not self.is_owner(ctx):
            return await ctx.send("Only the server owner can use this command.")

        self.data.pop(str(ctx.guild.id), None)
        save_data(self.data)

        await ctx.send("All auto roles have been cleared.")

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
