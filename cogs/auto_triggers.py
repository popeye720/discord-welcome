from discord.ext import commands
import discord
import json
import os
import time

# 👑 OWNER FROM ENV (Railway-safe)
def get_owner_id():
    try:
        return int(os.getenv("OWNER_ID", "0"))
    except ValueError:
        return 0

OWNER_ID = get_owner_id()
COOLDOWN_SECONDS = 60  # ⏱️ 1 minute

DATA_DIR = "data"
TRIGGER_FILE = os.path.join(DATA_DIR, "triggers.json")

# ---------------- LOAD / SAVE ----------------

def load_triggers():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(TRIGGER_FILE):
        with open(TRIGGER_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    try:
        with open(TRIGGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        # corrupted file → safe fallback
        return {}

def save_triggers(triggers):
    with open(TRIGGER_FILE, "w", encoding="utf-8") as f:
        json.dump(triggers, f, indent=4, ensure_ascii=False)

TRIGGERS = load_triggers()

# ---------------- COG ----------------

class AutoTriggers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # user_id : last_used_time

    # -------- AUTO REPLY --------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content.lower().strip()

        # ⏱️ cooldown per user
        now = time.time()
        last = self.cooldowns.get(message.author.id, 0)
        if now - last < COOLDOWN_SECONDS:
            return

        reply = TRIGGERS.get(content)
        if reply:
            self.cooldowns[message.author.id] = now
            await message.reply(reply, mention_author=False)

    # -------- ADD TRIGGER (OWNER ONLY) --------
    @commands.command(name="addtrigger")
    async def add_trigger(self, ctx, trigger: str, *, reply: str):
        if ctx.author.id != OWNER_ID:
            await ctx.reply("❌ You are not allowed to use this command.")
            return

        trigger = trigger.lower()
        TRIGGERS[trigger] = reply
        save_triggers(TRIGGERS)

        await ctx.reply(f"✅ Trigger `{trigger}` added & saved permanently!")

    # -------- DELETE TRIGGER (OWNER ONLY) --------
    @commands.command(name="deltrigger")
    async def delete_trigger(self, ctx, trigger: str):
        if ctx.author.id != OWNER_ID:
            await ctx.reply("❌ You are not allowed to use this command.")
            return

        trigger = trigger.lower()
        if trigger not in TRIGGERS:
            await ctx.reply(f"⚠️ Trigger `{trigger}` does not exist.")
            return

        del TRIGGERS[trigger]
        save_triggers(TRIGGERS)
        await ctx.reply(f"🗑️ Trigger `{trigger}` deleted successfully!")

    # -------- LIST TRIGGERS (OWNER ONLY) --------
    @commands.command(name="triggerlist")
    async def trigger_list(self, ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.reply("❌ You are not allowed to use this command.")
            return

        if not TRIGGERS:
            await ctx.reply("ℹ️ No triggers are set yet.")
            return

        # Discord embed description limit safe-guard
        names = sorted(TRIGGERS.keys())
        text = ", ".join(names)
        if len(text) > 4000:
            text = "\n".join(names)

        embed = discord.Embed(
            title="📋 Trigger List",
            description=text,
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

# REQUIRED FOR load_extension
async def setup(bot):
    await bot.add_cog(AutoTriggers(bot))
