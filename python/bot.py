import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import discord

load_dotenv()

"""
SETUP:
- Add custom role for TARGET_ROLE_NAME
- Ensure bot role is above TARGET_ROLE_NAME
"""

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DEV_MODE = os.environ.get("DEV_MODE", "")
TARGET_VC_CHANNEL_ID = os.environ.get("TARGET_VC_CHANNEL_ID", "")
TARGET_ROLE_NAME = os.environ.get("TARGET_ROLE_NAME", "")
GUILD_ID = os.environ.get("GUILD_ID", "")

if not all([DISCORD_BOT_TOKEN, TARGET_VC_CHANNEL_ID, TARGET_ROLE_NAME, GUILD_ID]):
    raise RuntimeError("Invalid .env config", [DISCORD_BOT_TOKEN, TARGET_VC_CHANNEL_ID, TARGET_ROLE_NAME, GUILD_ID])

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print("Bot is running...")

    target_guild = bot.get_guild(int(GUILD_ID))
    if not target_guild:
        raise RuntimeError(f"Could not find guild from ID {GUILD_ID}")

    target_role = discord.utils.get(target_guild.roles, name=TARGET_ROLE_NAME)
    if not target_role:
        raise RuntimeError(f"Could not find role from name {TARGET_ROLE_NAME}")


@bot.event
async def on_message(message):
    if DEV_MODE in ("true", "1"):
        if message.content == "!ping":
            await message.reply("Pong!")


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    target_guild = bot.get_guild(int(GUILD_ID))
    if not target_guild or member.guild.id != target_guild.id:
        return

    target_role = discord.utils.get(target_guild.roles, name=TARGET_ROLE_NAME)
    if not target_role:
        return

    now = datetime.now(timezone.utc)
    new_channel_id = str(after.channel.id) if after.channel else None
    old_channel_id = str(before.channel.id) if before.channel else None
    is_joined = new_channel_id == TARGET_VC_CHANNEL_ID
    is_left = old_channel_id == TARGET_VC_CHANNEL_ID and new_channel_id != TARGET_VC_CHANNEL_ID

    try:
        if is_joined:
            print(f"{member.id} joined {new_channel_id} @ {now}")
            if target_role not in member.roles:
                await member.add_roles(target_role)

        if is_left:
            print(f"{member.id} left {old_channel_id} @ {now}")
            if target_role in member.roles:
                await member.remove_roles(target_role)
    except Exception as error:
        print(f"An error occurred while processing role change: {error}")


bot.run(DISCORD_BOT_TOKEN)
