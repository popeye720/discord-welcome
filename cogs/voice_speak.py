import discord
from discord.ext import commands
import tempfile
import os
import asyncio
from gtts import gTTS

from database.mongo import db

# Mongo collection
speak_roles_col = db["speak_roles"]

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= ROLE MANAGEMENT =================

    @commands.command(name="addspeakrole")
    @commands.has_permissions(administrator=True)
    async def add_speak_role(self, ctx, role: discord.Role):
        exists = speak_roles_col.find_one({
            "guild_id": ctx.guild.id,
            "role_id": role.id
        })

        if exists:
            return await ctx.send("❌ Role already has speak permission.")

        speak_roles_col.insert_one({
            "guild_id": ctx.guild.id,
            "role_id": role.id
        })

        await ctx.send(f"✅ `{role.name}` can now use `!speak`")

    @commands.command(name="removespeakrole")
    @commands.has_permissions(administrator=True)
    async def remove_speak_role(self, ctx, role: discord.Role):
        result = speak_roles_col.delete_one({
            "guild_id": ctx.guild.id,
            "role_id": role.id
        })

        if result.deleted_count == 0:
            return await ctx.send("❌ Role not found in speak list.")

        await ctx.send(f"🗑️ `{role.name}` removed from speak permission")

    @commands.command(name="listspeakroles")
    async def list_speak_roles(self, ctx):
        roles = speak_roles_col.find({
            "guild_id": ctx.guild.id
        })

        role_mentions = []
        for r in roles:
            role = ctx.guild.get_role(r["role_id"])
            if role:
                role_mentions.append(role.mention)

        if not role_mentions:
            return await ctx.send("📭 No speak roles set.")

        await ctx.send(
            "**🗣️ Allowed Speak Roles:**\n" + "\n".join(role_mentions)
        )

    # ================= SPEAK COMMAND =================

    @commands.command(name="speak")
    async def speak(self, ctx, *, text: str):
        # Admin bypass
        allowed = ctx.author.guild_permissions.administrator

        # Role-based permission
        if not allowed:
            user_role_ids = [r.id for r in ctx.author.roles]
            allowed_role = speak_roles_col.find_one({
                "guild_id": ctx.guild.id,
                "role_id": {"$in": user_role_ids}
            })
            allowed = allowed_role is not None

        if not allowed:
            return await ctx.send("❌ You are not allowed to use `!speak`")

        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel first.")

        channel = ctx.author.voice.channel

        vc = ctx.voice_client
        if vc and vc.channel != channel:
            await vc.move_to(channel)
        elif not vc:
            vc = await channel.connect()

        # Create TTS
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            gTTS(text=text, lang="hi").save(f.name)
            audio_path = f.name

        def after_playing(error):
            os.remove(audio_path)
            asyncio.run_coroutine_threadsafe(
                vc.disconnect(),
                self.bot.loop
            )

        vc.play(
            discord.FFmpegPCMAudio(audio_path),
            after=after_playing
        )

        await ctx.send(f"🗣️ Speaking: `{text}`")

async def setup(bot):
    await bot.add_cog(Voice(bot))
