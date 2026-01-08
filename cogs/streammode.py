import discord
from discord.ext import commands
from database.models import streammode_col


class StreamMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- OWNER / ADMIN CHECK ----------
    def has_permission(self, ctx):
        return (
            ctx.guild
            and (
                ctx.author.id == ctx.guild.owner_id
                or ctx.author.guild_permissions.administrator
            )
        )

    # ---------------- STREAM MODE ON ----------------
    @commands.command(name="streammode")
    @commands.guild_only()
    async def streammode(self, ctx):
        if not self.has_permission(ctx):
            return await ctx.send(
                "❌ Only **Server Owner or Admin** can enable stream mode."
            )

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                "❌ You must be connected to a voice channel."
            )

        vc = ctx.author.voice.channel

        existing = streammode_col.find_one({"guild_id": ctx.guild.id})
        if existing:
            return await ctx.send("⚠️ Stream mode is already ENABLED.")

        streammode_col.insert_one({
            "guild_id": ctx.guild.id,
            "vc_id": vc.id,
            "enabled": True
        })

        await ctx.send(
            f"✅ **Stream Mode Enabled**\n\n"
            f"🔒 All bots are now blocked from joining **{vc.name}**"
        )

    # ---------------- STREAM MODE OFF ----------------
    @commands.command(name="streamoff")
    @commands.guild_only()
    async def streamoff(self, ctx):
        if not self.has_permission(ctx):
            return await ctx.send(
                "❌ Only **Server Owner or Admin** can disable stream mode."
            )

        result = streammode_col.delete_one({"guild_id": ctx.guild.id})
        if result.deleted_count == 0:
            return await ctx.send("⚠️ Stream mode is already OFF.")

        await ctx.send(
            "🟢 **Stream Mode Disabled**\n"
            "Bots can now join voice channels."
        )

    # ---------------- STATUS COMMAND ----------------
    @commands.command(name="statusstream")
    @commands.guild_only()
    async def statusstream(self, ctx):
        if not self.has_permission(ctx):
            return await ctx.send(
                "❌ Only **Server Owner or Admin** can view stream status."
            )

        data = streammode_col.find_one({"guild_id": ctx.guild.id})
        if not data:
            return await ctx.send("🔴 **Stream Mode Status:** OFF")

        vc = ctx.guild.get_channel(data["vc_id"])
        vc_name = vc.name if vc else "Unknown"

        await ctx.send(
            f"🟢 **Stream Mode Status:** ON\n"
            f"🔒 Blocked VC: **{vc_name}**\n"
            f"🤖 All bots are blocked from joining this VC."
        )

    # ---------------- BLOCK ALL BOTS ----------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.guild or not member.bot:
            return

        data = streammode_col.find_one({"guild_id": member.guild.id})
        if not data or not data.get("enabled"):
            return

        if after.channel and after.channel.id == data["vc_id"]:
            try:
                await member.move_to(None)
            except:
                pass


async def setup(bot):
    await bot.add_cog(StreamMode(bot))
