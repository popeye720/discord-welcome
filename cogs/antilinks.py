import re
import discord
from discord.ext import commands
from database.models import antilinks_col  # 👈 Mongo collection

LINK_REGEX = re.compile(
    r"(https?:\/\/|www\.)\S+",
    re.IGNORECASE
)

class AntiLinks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------------------
    # PERMISSION CHECK
    # -------------------------------
    def is_admin_or_owner(self, member: discord.Member):
        if member.id == member.guild.owner_id:
            return True
        return member.guild_permissions.administrator

    # -------------------------------
    # ENABLE ANTILINKS
    # -------------------------------
    @commands.command(name="antilinks")
    @commands.guild_only()
    async def antilinks(self, ctx, role: discord.Role = None):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        allowed_roles = []
        if role:
            allowed_roles.append(role.id)

        antilinks_col.update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "guild_id": ctx.guild.id,
                    "enabled": True,
                    "allowed_roles": allowed_roles
                }
            },
            upsert=True
        )

        if role:
            await ctx.reply(
                f"✅ **Anti-Links Enabled**\n\n"
                f"🔓 Allowed Role: {role.mention}\n"
                f"👑 Admins & Owner always allowed"
            )
        else:
            await ctx.reply(
                f"✅ **Anti-Links Enabled**\n\n"
                f"🔒 Only **Admins & Owner** can send links"
            )

    # -------------------------------
    # DISABLE ANTILINKS
    # -------------------------------
    @commands.command(name="offantilinks")
    @commands.guild_only()
    async def offantilinks(self, ctx):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        antilinks_col.delete_one({"guild_id": ctx.guild.id})

        await ctx.reply("🟢 **Anti-Links Disabled**\nAll restrictions removed.")

    # -------------------------------
    # MESSAGE LISTENER
    # -------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        data = antilinks_col.find_one(
            {"guild_id": message.guild.id, "enabled": True},
            {"allowed_roles": 1}
        )

        if not data:
            return

        if not LINK_REGEX.search(message.content):
            return

        # 👑 Owner allowed
        if message.author.id == message.guild.owner_id:
            return

        # 🛡 Admin allowed
        if message.author.guild_permissions.administrator:
            return

        # 🎭 Role exception
        allowed_roles = data.get("allowed_roles", [])
        if allowed_roles:
            user_role_ids = [role.id for role in message.author.roles]
            if any(rid in user_role_ids for rid in allowed_roles):
                return

        # ❌ DELETE MESSAGE
        try:
            await message.delete()
        except discord.Forbidden:
            return

        # 📩 DM USER
        try:
            embed = discord.Embed(
                title="🚫 Links Not Allowed",
                description=(
                    f"Hey **{message.author.name}** 👋\n\n"
                    f"Links are **not allowed** in this server."
                ),
                color=discord.Color.red()
            )
            await message.author.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(AntiLinks(bot))
