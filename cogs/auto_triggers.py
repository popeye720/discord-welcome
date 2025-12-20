from discord.ext import commands
import discord
import json
import os
import time

# 👑 OWNER FROM ENV (Railway-safe)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
COOLDOWN_SECONDS = 60  # ⏱️ 1 minute

DATA_DIR = "data"
TRIGGER_FILE = f"{DATA_DIR}/triggers.json"

# ---------------- LOAD / SAVE ----------------

def load_triggers():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(TRIGGER_FILE):
        with open(TRIGGER_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    with open(TRIGGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_triggers(triggers):
    with open(TRIGGER_FILE, "w", encoding="utf-8") as f:
        json.dump(triggers, f, indent=4)

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

# REQUIRED FOR load_extension
async def setup(bot):
    await bot.add_cog(AutoTriggers(bot))
