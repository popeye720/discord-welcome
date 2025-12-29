import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/jtc.json"

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

class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()
        self.temp_channels = {}   # vc_id : creator_id
        self._ready_done = False  # on_ready guard

    # ================= OWNER CHECK =================
    def is_owner(self, ctx):
        return ctx.guild and ctx.author.id == ctx.guild.owner_id

    # ================= BOT READY =================
    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_done:
            return
        self._ready_done = True

        for guild in self.bot.guilds:
            await self.setup_jtc(guild)

    async def setup_jtc(self, guild: discord.Guild):
        guild_id = str(guild.id)
        conf = self.data.get(guild_id)

        if not conf:
            return

        category = guild.get_channel(conf["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return

        # 🔥 delete old JTC safely
        old_channel = guild.get_channel(conf["jtc_channel_id"])
        if isinstance(old_channel, discord.VoiceChannel):
            try:
                await old_channel.delete()
            except:
                pass

        # 🟢 create fresh JTC
        channel = await guild.create_voice_channel(
            name="➕ Join to Create",
            category=category
        )

        self.data[guild_id]["jtc_channel_id"] = channel.id
        save_data(self.data)

    # ================= OWNER COMMAND =================
    @commands.command(name="createjtc")
    async def create_jtc(self, ctx, category_id: int):
        if not self.is_owner(ctx):
            return await ctx.reply("❌ Only the **server owner** can use this command.")

        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await ctx.reply("❌ Invalid category ID.")

        guild_id = str(ctx.guild.id)

        # 🔥 delete existing JTC if present
        if guild_id in self.data:
            old = ctx.guild.get_channel(self.data[guild_id]["jtc_channel_id"])
            if isinstance(old, discord.VoiceChannel):
                await old.delete()

        channel = await ctx.guild.create_voice_channel(
            name="➕ Join to Create",
            category=category
        )

        self.data[guild_id] = {
            "category_id": category.id,
            "jtc_channel_id": channel.id
        }
        save_data(self.data)

        await ctx.reply(
            f"✅ **Join-to-Create VC ready**\n"
            f"📂 Category: **{category.name}**"
        )

    # ================= VOICE LISTENER =================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild_id = str(member.guild.id)
        conf = self.data.get(guild_id)

        if not conf:
            return

        jtc_id = conf["jtc_channel_id"]

        # 🟢 User joined JTC
        if after.channel and after.channel.id == jtc_id:
            guild = member.guild
            category = after.channel.category

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(
                    connect=True,
                    manage_channels=True,
                    move_members=True
                )
            }

            vc = await guild.create_voice_channel(
                name=f"{member.name}'s VC",
                category=category,
                overwrites=overwrites
            )

            await member.move_to(vc)
            self.temp_channels[vc.id] = member.id

        # 🔴 Delete empty temp VC
        if before.channel and before.channel.id in self.temp_channels:
            vc = before.channel

            if not vc.members:
                try:
                    await vc.delete()
                except:
                    pass
                self.temp_channels.pop(vc.id, None)

    # ================= CLEANUP =================
    def cog_unload(self):
        save_data(self.data)

# ================= SETUP =================
async def setup(bot):
    await bot.add_cog(JoinToCreate(bot))
