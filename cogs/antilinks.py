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
        return (
            member.id == member.guild.owner_id
            or member.guild_permissions.administrator
        )

    # -------------------------------
    # ENABLE / ADD ROLE
    # -------------------------------
    @commands.command(name="antilinks")
    @commands.guild_only()
    async def antilinks(self, ctx, role: discord.Role = None):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        data = antilinks_col.find_one({"guild_id": ctx.guild.id})

        # 🟢 FIRST TIME ENABLE
        if not data:
            antilinks_col.insert_one({
                "guild_id": ctx.guild.id,
                "enabled": True,
                "allowed_roles": [role.id] if role else []
            })

            if role:
                return await ctx.reply(
                    f"✅ **Anti-Links Enabled**\n"
                    f"🔓 Allowed Role: {role.mention}"
                )
            return await ctx.reply(
                "✅ **Anti-Links Enabled**\n"
                "🔒 Only **Admins & Owner** can send links"
            )

        # 🔁 ALREADY ENABLED
        if data.get("enabled"):
            if not role:
                return await ctx.reply("⚠️ **Anti-Links is already ENABLED**.")

            allowed_roles = data.get("allowed_roles", [])

            if role.id in allowed_roles:
                return await ctx.reply(
                    f"⚠️ {role.mention} is **already allowed**."
                )

            antilinks_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$push": {"allowed_roles": role.id}}
            )

            return await ctx.reply(
                f"✅ Role Added: {role.mention} can now send links."
            )

    # -------------------------------
    # DISABLE ANTILINKS
    # -------------------------------
    @commands.command(name="offantilinks")
    @commands.guild_only()
    async def offantilinks(self, ctx):
        if not self.is_admin_or_owner(ctx.author):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        data = antilinks_col.find_one({"guild_id": ctx.guild.id})

        if not data:
            return await ctx.reply("⚠️ **Anti-Links is already DISABLED**.")

        antilinks_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.reply("🟢 **Anti-Links Disabled Successfully**.")

    # -------------------------------
    # STATUS COMMAND
    # -------------------------------
    @commands.command(name="statusantilinks")
    @commands.guild_only()
    async def statusantilinks(self, ctx):
        data = antilinks_col.find_one({"guild_id": ctx.guild.id})

        if not data:
            return await ctx.reply("🔴 **Anti-Links Status:** OFF")

        role_mentions = []
        for rid in data.get("allowed_roles", []):
            role = ctx.guild.get_role(rid)
            if role:
                role_mentions.append(role.mention)

        embed = discord.Embed(
            title="🔗 Anti-Links Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Status",
            value="🟢 ENABLED",
            inline=False
        )

        embed.add_field(
            name="Allowed Users",
            value="👑 Admins & Server Owner",
            inline=False
        )

        embed.add_field(
            name="Allowed Roles",
            value=", ".join(role_mentions) if role_mentions else "None",
            inline=False
        )

        await ctx.reply(embed=embed)

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

        # -------------------------------
        # ALLOW !audiodown COMMAND
        # -------------------------------
        if message.content.startswith("!audiodown "):
            # Always allow for anyone (admin, owner, normal user)
            return

        # -------------------------------
        # CHECK FOR LINKS
        # -------------------------------
        if not LINK_REGEX.search(message.content):
            return

        # 👑 OWNER
        if message.author.id == message.guild.owner_id:
            return

        # 🛡 ADMIN
        if message.author.guild_permissions.administrator:
            return

        # 🎭 ROLE EXCEPTION
        allowed_roles = data.get("allowed_roles", [])
        if allowed_roles:
            if any(r.id in allowed_roles for r in message.author.roles):
                return

        # ❌ DELETE if message is ONLY a link
        if message.content.strip() == LINK_REGEX.search(message.content).group(0):
            try:
                await message.delete()
            except discord.Forbidden:
                return

            # 📩 DM
            try:
                await message.author.send(
                    embed=discord.Embed(
                        title="🚫 Links Not Allowed",
                        description="You are not allowed to send links in this server.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(AntiLinks(bot))
