from discord.ext import commands
import discord
import time

from database.models import autotrigger_col

COOLDOWN_SECONDS = 10  # 10 seconds


class AutoTriggers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # user_id : last_used_time

    # -------- AUTO REPLY --------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.lower().strip()

        # cooldown per user
        now = time.time()
        last = self.cooldowns.get(message.author.id, 0)
        if now - last < COOLDOWN_SECONDS:
            return

        data = autotrigger_col.find_one({
            "guild_id": message.guild.id,
            "trigger": content
        })

        if data:
            self.cooldowns[message.author.id] = now
            await message.reply(
                data["reply"],
                mention_author=False
            )

    # -------- ADD TRIGGER (OWNER / ADMIN ONLY) --------
    @commands.command(name="addtrigger")
    async def add_trigger(self, ctx, trigger: str, *, reply: str):
        if not ctx.guild or not (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        trigger = trigger.lower()

        existing = autotrigger_col.find_one({
            "guild_id": ctx.guild.id,
            "trigger": trigger
        })
        if existing:
            return await ctx.reply(
                f"Trigger `{trigger}` already exists."
            )

        autotrigger_col.insert_one({
            "guild_id": ctx.guild.id,
            "trigger": trigger,
            "reply": reply
        })

        await ctx.reply(f"✅ Trigger `{trigger}` added and saved permanently.")

    # -------- DELETE TRIGGER (OWNER / ADMIN ONLY) --------
    @commands.command(name="deltrigger")
    async def delete_trigger(self, ctx, trigger: str):
        if not ctx.guild or not (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        trigger = trigger.lower()

        result = autotrigger_col.find_one_and_delete({
            "guild_id": ctx.guild.id,
            "trigger": trigger
        })

        if not result:
            return await ctx.reply(f"Trigger `{trigger}` does not exist.")

        await ctx.reply(f"✅ Trigger `{trigger}` deleted successfully.")

    # -------- LIST TRIGGERS (OWNER / ADMIN ONLY) --------
    @commands.command(name="triggerlist")
    async def trigger_list(self, ctx):
        if not ctx.guild or not (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return await ctx.reply("❌ Only **Admin or Server Owner** can use this command.")

        triggers = autotrigger_col.find(
            {"guild_id": ctx.guild.id},
            {"trigger": 1, "_id": 0}
        )

        names = sorted(t["trigger"] for t in triggers)

        if not names:
            return await ctx.reply("No triggers are set yet.")

        text = ", ".join(names)
        if len(text) > 4000:
            text = "\n".join(names)

        embed = discord.Embed(
            title="Trigger List",
            description=text,
            color=discord.Color.blurple()
        )

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(AutoTriggers(bot))
