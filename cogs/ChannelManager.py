import discord
from discord.ext import commands

class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= CREATE VC =================

    @commands.command(name="createvc")
    @commands.has_permissions(manage_channels=True)
    async def create_vc(self, ctx, *, name: str):
        channel = await ctx.guild.create_voice_channel(name=name)
        await ctx.send(f"✅ Voice channel created: **{channel.name}**")

    # ================= CREATE TC =================

    @commands.command(name="createtc")
    @commands.has_permissions(manage_channels=True)
    async def create_tc(self, ctx, *, name: str):
        channel = await ctx.guild.create_text_channel(name=name)
        await ctx.send(f"✅ Text channel created: **{channel.name}**")

    # ================= EDIT VC =================

    @commands.command(name="editvc")
    @commands.has_permissions(manage_channels=True)
    async def edit_vc(self, ctx, channel_id: int, *, new_name: str):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("❌ Voice channel not found.")

        await channel.edit(name=new_name)
        await ctx.send(f"✏️ Voice channel renamed to **{new_name}**")

    # ================= EDIT TC =================

    @commands.command(name="edittc")
    @commands.has_permissions(manage_channels=True)
    async def edit_tc(self, ctx, channel_id: int, *, new_name: str):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.TextChannel):
            return await ctx.send("❌ Text channel not found.")

        await channel.edit(name=new_name)
        await ctx.send(f"✏️ Text channel renamed to **{new_name}**")

    # ================= DELETE VC =================

    @commands.command(name="delvc")
    @commands.has_permissions(manage_channels=True)
    async def delete_vc(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("❌ Voice channel not found.")

        await channel.delete()
        await ctx.send("🗑️ Voice channel deleted.")

    # ================= DELETE TC =================

    @commands.command(name="deltc")
    @commands.has_permissions(manage_channels=True)
    async def delete_tc(self, ctx, channel_id: int):
        channel = ctx.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.TextChannel):
            return await ctx.send("❌ Text channel not found.")

        await channel.delete()
        await ctx.send("🗑️ Text channel deleted.")
    # ================= CREATE CATEGORY =================

    @commands.command(name="createcat")
    @commands.has_permissions(manage_channels=True)
    async def create_category(self, ctx, *, name: str):
        category = await ctx.guild.create_category(name=name)
        await ctx.send(f"✅ Category created: **{category.name}**")

    # ================= EDIT CATEGORY =================

    @commands.command(name="editcat")
    @commands.has_permissions(manage_channels=True)
    async def edit_category(self, ctx, category_id: int, *, new_name: str):
        category = ctx.guild.get_channel(category_id)

        if not category or not isinstance(category, discord.CategoryChannel):
            return await ctx.send("❌ Category not found.")

        await category.edit(name=new_name)
        await ctx.send(f"✏️ Category renamed to **{new_name}**")
        
    # ================= DELETE CATEGORY =================

    @commands.command(name="delcat")
    @commands.has_permissions(manage_channels=True)
    async def delete_category(self, ctx, category_id: int):
        category = ctx.guild.get_channel(category_id)

        if not category or not isinstance(category, discord.CategoryChannel):
            return await ctx.send("❌ Category not found.")

        await category.delete()
        await ctx.send("🗑️ Category deleted.")

# ================= SETUP =================

async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
