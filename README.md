🤖 Discord Bot (All-in-One Discord Utility Bot)

A powerful, modular & scalable Discord bot built with Python & discord.py, designed to handle welcome systems, moderation, music, automation, utilities, games, server management, and more — all in one bot.

This project is production-ready and structured using Cogs, making it easy to maintain and scale for 50 → 1000+ servers.

✨ Features Overview
🛠 Core System

Slash command based (/)

Cog-based architecture (clean & modular)

MongoDB support (persistent data)

Production-ready logging & error handling

Docker support (Railway / VPS / Cloud ready)

👋 Welcome & Greetings

Custom welcome messages

Auto greetings system

DM welcome messages

Auto triggers on join

Auto role on join

🛡 Moderation & Security

Anti-link system

Anti-spam protection

Auto moderation

Server permission checks

Stream mode (safe chat mode)

🎵 Music System

Advanced music bot (Wavelink / Lavalink based)

YouTube search & URL support

Queue system

Auto disconnect when idle

High quality audio playback

Multi-server supported

🔊 Voice & Channel Management

Join-to-Create private voice channels

Auto rename voice channels

Private VC system

Channel manager tools

🎮 Fun & Utility

Fun games

Poll system

Feedback system

Forms & modals

Reaction roles

Server stats & profiles

User profile system

Search utilities

Free games notifier (Epic / Steam)

⏰ Automation

Scheduled embeds

Auto ping system

YouTube notification system

Chat polling

Auto messages

📁 Project Structure


discord-welcome/
│
├── main.py                  # Bot entry point
├── requirements.txt         # Python dependencies
├── runtime.txt              # Python runtime (for Railway)
├── Dockerfile               # Docker support
│
├── cogs/                    # All bot features (modular)
│   ├── music.py
│   ├── greetings.py
│   ├── autorole.py
│   ├── antispam.py
│   ├── antilinks.py
│   ├── ticket.py
│   ├── reactionRole.py
│   ├── join_to_create.py
│   ├── privatevc.py
│   └── ...many more
│
├── database/
│   ├── mongo.py             # MongoDB connection
│   └── models.py            # Database models
│
├── utils/
│   ├── interaction.py
│   └── permissions.py
