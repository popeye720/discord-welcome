import discord
from discord.ext import commands


class ChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= PERMISSION CHECK =================
    def can_manage(self, ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False

        return (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
            or ctx.author.guild_permissions.manage_channels
        )

    # ================= CREATE VOICE CHANNEL =================

    @commands.command(name="createvc")
    async def create_vc(self, ctx, *, name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = await ctx.guild.create_voice_channel(name=name)
        await ctx.send(f"Voice channel created: {channel.name}")

    # ================= CREATE TEXT CHANNEL =================

    @commands.command(name="createtc")
    async def create_tc(self, ctx, *, name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = await ctx.guild.create_text_channel(name=name)
        await ctx.send(f"Text channel created: {channel.name}")

    # ================= EDIT VOICE CHANNEL =================

    @commands.command(name="editvc")
    async def edit_vc(self, ctx, channel_id: int, *, new_name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("Voice channel not found.")

        await channel.edit(name=new_name)
        await ctx.send(f"Voice channel renamed to {new_name}")

    # ================= EDIT TEXT CHANNEL =================

    @commands.command(name="edittc")
    async def edit_tc(self, ctx, channel_id: int, *, new_name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("Text channel not found.")

        await channel.edit(name=new_name)
        await ctx.send(f"Text channel renamed to {new_name}")

    # ================= DELETE VOICE CHANNEL =================

    @commands.command(name="delvc")
    async def delete_vc(self, ctx, channel_id: int):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            return await ctx.send("Voice channel not found.")

        await channel.delete()
        await ctx.send("Voice channel deleted.")

    # ================= DELETE TEXT CHANNEL =================

    @commands.command(name="deltc")
    async def delete_tc(self, ctx, channel_id: int):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("Text channel not found.")

        await channel.delete()
        await ctx.send("Text channel deleted.")

    # ================= CREATE CATEGORY =================

    @commands.command(name="createcat")
    async def create_category(self, ctx, *, name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        category = await ctx.guild.create_category(name=name)
        await ctx.send(f"Category created: {category.name}")

    # ================= EDIT CATEGORY =================

    @commands.command(name="editcat")
    async def edit_category(self, ctx, category_id: int, *, new_name: str):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.send("Category not found.")

        await category.edit(name=new_name)
        await ctx.send(f"Category renamed to {new_name}")

    # ================= DELETE CATEGORY =================

    @commands.command(name="delcat")
    async def delete_category(self, ctx, category_id: int):
        if not self.can_manage(ctx):
            return await ctx.send("You do not have permission to use this command.")

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.send("Category not found.")

        await category.delete()
        await ctx.send("Category deleted.")


# ================= CLEAR MESSAGES =================

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearmsg")
    async def clearmsg(self, ctx, *channel_ids: int):
        if not ctx.guild:
            return

        # Owner OR Admin
        if not (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return await ctx.send("You do not have permission to use this command.")

        if not channel_ids:
            return await ctx.send("Please provide at least one channel ID.")

        if len(channel_ids) > 3:
            return await ctx.send("You can clear a maximum of 3 channels at once.")

        results = []

        for channel_id in channel_ids:
            channel = ctx.guild.get_channel(channel_id)

            if not channel:
                results.append(f"{channel_id} : Invalid channel ID.")
                continue

            if channel.type == discord.ChannelType.category:
                results.append(f"{channel.name} : Categories cannot be cleared.")
                continue

            try:
                deleted = await channel.purge(limit=None, bulk=True)
            except discord.Forbidden:
                results.append(f"{channel.mention} : Missing permissions.")
                continue
            except discord.HTTPException:
                results.append(f"{channel.mention} : API error.")
                continue

            if not deleted:
                results.append(f"{channel.mention} : No messages to delete.")
            else:
                results.append(
                    f"{channel.mention} : Deleted {len(deleted)} messages."
                )

        await ctx.send("\n".join(results))


# ================= SETUP =================

async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
    await bot.add_cog(ClearMessages(bot))
