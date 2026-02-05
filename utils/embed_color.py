import discord

# Centralized embed color (Royal / Dodger Blue)
EMBED_COLOR = discord.Color.from_rgb(2, 102, 255)

# Optional helper (recommended)
def create_embed(
    title: str | None = None,
    description: str | None = None
) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=EMBED_COLOR
    )