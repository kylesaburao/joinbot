# Joinbot

MOVED TO https://github.com/ssss-sfu/coursebot.

Intended for Software Systems Student Society (Study Time).

A Discord bot that automatically assigns a role to members when they join a specific voice channel, and removes it when they leave.

This role will control visibilty of certain text channels such that only users in a given voice channel can see those text channels.

## Setup

1. Create a custom role in your Discord server for `TARGET_ROLE_NAME`
2. Ensure the bot's role is **above** `TARGET_ROLE_NAME` in the role hierarchy
3. Create a `.env` file with the following:

```
DISCORD_BOT_TOKEN=
GUILD_ID=
TARGET_VC_CHANNEL_ID=
TARGET_ROLE_NAME=
DEV_MODE=          # optional, set to "true" or "1"
```

## Implementations

There are two equivalent implementations:

### Node (TypeScript)

```sh
cd node
npm install
npm run dev     # development with ts-node
npm run build   # compile
npm start       # run compiled output
```

### Python

```sh
cd python
pip install -r requirements.txt
python bot.py
```

## Required Bot Permissions

- Manage Roles
- Voice Status
