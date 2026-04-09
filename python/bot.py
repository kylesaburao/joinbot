import os
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import Optional
import discord
from discord.ext import tasks

load_dotenv()

"""
SETUP:
- Add custom role for TARGET_ROLE_NAME
- Ensure bot role is above TARGET_ROLE_NAME
"""

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
TARGET_VC_CHANNEL_ID = int(os.environ.get("TARGET_VC_CHANNEL_ID", "0"))
TARGET_ROLE_NAME = os.environ.get("TARGET_ROLE_NAME", "")

JOIN_LIMIT_COUNT = int(os.environ.get("JOIN_LIMIT_COUNT", "5"))
JOIN_LIMIT_WINDOW_SECONDS = int(os.environ.get("JOIN_LIMIT_WINDOW_SECONDS", "60"))

# Short-stay abuse detection: if a user has SHORT_STAY_THRESHOLD or more
# visits shorter than SHORT_STAY_SECONDS within the tracking window,
# they are blocked from receiving the role.
SHORT_STAY_SECONDS = int(os.environ.get("SHORT_STAY_SECONDS", "30"))
SHORT_STAY_THRESHOLD = int(os.environ.get("SHORT_STAY_THRESHOLD", "5"))
SHORT_STAY_WINDOW_SECONDS = int(os.environ.get("SHORT_STAY_WINDOW_SECONDS", "120"))
CLEANUP_INTERVAL_SECONDS = max(JOIN_LIMIT_WINDOW_SECONDS, SHORT_STAY_WINDOW_SECONDS) * 2

if not all([DISCORD_BOT_TOKEN, TARGET_VC_CHANNEL_ID, TARGET_ROLE_NAME]):
    raise RuntimeError("Invalid .env config")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = discord.Client(intents=intents)

# target_guild: Optional[discord.Guild] = None
# target_role: Optional[discord.Role] = None
join_history: dict[int, list[datetime]] = defaultdict(list)
short_stay_history: dict[int, list[datetime]] = defaultdict(list)
user_joined_at: dict[int, datetime] = {}


def format_eta(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs}s" if minutes > 0 else f"{secs}s"


def prune_timestamps(timestamps: list[datetime], window_start: datetime) -> list[datetime]:
    return [t for t in timestamps if t > window_start]


async def send_dm(member: discord.Member, message: str):
    try:
        await member.send(message)
    except:
        print(f'Encountered error sending message to user')

@tasks.loop(seconds=CLEANUP_INTERVAL_SECONDS)
async def cleanup_stale_history():
    now = datetime.now(timezone.utc)
    join_window_start = now - timedelta(seconds=JOIN_LIMIT_WINDOW_SECONDS)
    short_stay_window_start = now - timedelta(seconds=SHORT_STAY_WINDOW_SECONDS)

    for user_id in list(join_history.keys()):
        join_history[user_id] = prune_timestamps(join_history[user_id], join_window_start)
        if not join_history[user_id]:
            del join_history[user_id]

    for user_id in list(short_stay_history.keys()):
        short_stay_history[user_id] = prune_timestamps(short_stay_history[user_id], short_stay_window_start)
        if not short_stay_history[user_id]:
            del short_stay_history[user_id]

    # Clean up user_joined_at entries older than the largest window
    stale_threshold = now - timedelta(seconds=max(JOIN_LIMIT_WINDOW_SECONDS, SHORT_STAY_WINDOW_SECONDS))
    for user_id in list(user_joined_at.keys()):
        if user_joined_at[user_id] < stale_threshold:
            del user_joined_at[user_id]


@bot.event
async def on_ready():
    print("Bot is running...")
    if not cleanup_stale_history.is_running():
        cleanup_stale_history.start()


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    target_role = discord.utils.get(member.guild.roles, name=TARGET_ROLE_NAME)
    if not target_role:
        print(f'Unable to locate role "{TARGET_ROLE_NAME}" through member context')
        return

    now = datetime.now(timezone.utc)
    new_channel_id = after.channel.id if after.channel else None
    old_channel_id = before.channel.id if before.channel else None
    is_joined = new_channel_id == TARGET_VC_CHANNEL_ID and old_channel_id != TARGET_VC_CHANNEL_ID
    is_left = old_channel_id == TARGET_VC_CHANNEL_ID and new_channel_id != TARGET_VC_CHANNEL_ID

    try:
        if is_joined:
            print(f"{member.id} joined {new_channel_id} @ {now}")
            user_joined_at[member.id] = now

            # Prune join history and check frequency limit
            join_history[member.id] = prune_timestamps(
                join_history[member.id], now - timedelta(seconds=JOIN_LIMIT_WINDOW_SECONDS)
            )

            # Check join frequency limit before recording this join (AVOID DoS)
            if len(join_history[member.id]) >= JOIN_LIMIT_COUNT:
                print(f"{member.id} exceeded join limit ({JOIN_LIMIT_COUNT} in {JOIN_LIMIT_WINDOW_SECONDS}s)")
                oldest = join_history[member.id][0]
                remaining = max(1, int((oldest + timedelta(seconds=JOIN_LIMIT_WINDOW_SECONDS) - now).total_seconds()))
                await send_dm(
                    member,
                    f"You are joining Study Time too frequently. "
                    f"Please wait {format_eta(remaining)} before rejoining to have access to the chat.",
                )
                return

            join_history[member.id].append(now)

            # Check short-stay abuse
            short_stay_history[member.id] = prune_timestamps(
                short_stay_history[member.id], now - timedelta(seconds=SHORT_STAY_WINDOW_SECONDS)
            )
            if len(short_stay_history[member.id]) >= SHORT_STAY_THRESHOLD:
                print(f"{member.id} flagged for short-stay abuse ({len(short_stay_history[member.id])} short visits)")
                oldest = short_stay_history[member.id][0]
                remaining = max(1, int((oldest + timedelta(seconds=SHORT_STAY_WINDOW_SECONDS) - now).total_seconds()))
                await send_dm(
                    member,
                    f"You have been joining Study Time for very short periods too often. "
                    f"Please wait {format_eta(remaining)} before rejoining to have access to the chat."
                )
                return

            if target_role not in member.roles:
                await member.add_roles(target_role)

        elif is_left:
            print(f"{member.id} left {old_channel_id} @ {now}")

            # Record short stay if applicable
            join_time = user_joined_at.pop(member.id, None)
            short_stay_duration = (now - join_time).total_seconds() if join_time is not None else None
            if (short_stay_duration is not None) and (short_stay_duration < SHORT_STAY_SECONDS):
                print(f"{member.id} short stay: {short_stay_duration:.0f}s")
                short_stay_history[member.id] = prune_timestamps(
                    short_stay_history[member.id], now - timedelta(seconds=SHORT_STAY_WINDOW_SECONDS)
                )
                short_stay_history[member.id].append(now)

            if target_role in member.roles:
                await member.remove_roles(target_role)
    except Exception as error:
        print(f"An error occurred while processing role change: {error}")


bot.run(DISCORD_BOT_TOKEN)
