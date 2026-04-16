"""
Telegram Group Broadcaster
---------------------------
Login with your Telegram account and broadcast a text message
OR forward an existing message to every group you have joined.

Two intervals:
  • Send interval  – gap (seconds) between each group send within a round
  • Round interval – sleep time (seconds) after ALL groups are done,
                     before the next round starts (runs forever until Ctrl+C)

Requirements:
    pip install telethon

Usage:
    python telegram_broadcaster.py
"""

import asyncio
import sys
from telethon import TelegramClient
from telethon.tl.types import (
    Chat, Channel, ChatForbidden, ChannelForbidden
)
from telethon.errors import (
    FloodWaitError, ChatWriteForbiddenError,
    UserBannedInChannelError, ChannelPrivateError
)

# ─────────────────────────────────────────────
#  Telegram API credentials
#  Get yours at https://my.telegram.org/apps
# ─────────────────────────────────────────────
API_ID   = 21752358   # e.g. 1234567
API_HASH = "fb46a136fed4a4de27ab057c7027fec3"   # e.g. "abcdef1234567890abcdef1234567890"

SESSION_NAME = "adbot01"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def prompt(msg: str, default: str = "") -> str:
    try:
        val = input(msg).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)


def fmt_seconds(secs: float) -> str:
    """Human-readable time string."""
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


async def get_all_groups(client) -> list:
    """Return every dialog that is a group or supergroup/channel."""
    groups = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (ChatForbidden, ChannelForbidden)):
            continue
        if isinstance(entity, Chat):
            groups.append(dialog)
        elif isinstance(entity, Channel) and (entity.megagroup or entity.broadcast is False):
            groups.append(dialog)
        elif isinstance(entity, Channel):
            groups.append(dialog)
    return groups


async def round_countdown(seconds: float):
    """Live countdown before the next round."""
    print()
    remaining = int(seconds)
    while remaining > 0:
        print(f"\r  🔄  Next round in {fmt_seconds(remaining)} … (Ctrl+C to stop)   ", end="", flush=True)
        await asyncio.sleep(1)
        remaining -= 1
    print(f"\r  ✅  Round interval done. Starting next round…{' '*30}")


async def broadcast_text(client, groups: list, text: str, send_interval: float) -> tuple:
    """Send a text message to every group. Returns (success, failed)."""
    total   = len(groups)
    success = 0
    failed  = 0

    for idx, dialog in enumerate(groups, 1):
        name = dialog.name or str(dialog.id)
        try:
            await client.send_message(dialog.entity, text)
            print(f"  ✅  [{idx}/{total}]  {name}")
            success += 1
        except FloodWaitError as e:
            print(f"  ⏳  FloodWait – sleeping {e.seconds}s then retrying…")
            await asyncio.sleep(e.seconds)
            try:
                await client.send_message(dialog.entity, text)
                print(f"  ✅  [{idx}/{total}]  {name}  (after flood wait)")
                success += 1
            except Exception as err:
                print(f"  ❌  [{idx}/{total}]  {name}  →  {err}")
                failed += 1
        except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError) as e:
            print(f"  ⛔  [{idx}/{total}]  {name}  →  {type(e).__name__}")
            failed += 1
        except Exception as e:
            print(f"  ❌  [{idx}/{total}]  {name}  →  {e}")
            failed += 1

        if idx < total:
            await asyncio.sleep(send_interval)

    return success, failed


async def broadcast_forward(client, groups: list, source_chat, message_id: int, send_interval: float) -> tuple:
    """Forward a specific message to every group. Returns (success, failed)."""
    total   = len(groups)
    success = 0
    failed  = 0

    for idx, dialog in enumerate(groups, 1):
        name = dialog.name or str(dialog.id)
        try:
            await client.forward_messages(dialog.entity, message_id, source_chat)
            print(f"  ✅  [{idx}/{total}]  {name}")
            success += 1
        except FloodWaitError as e:
            print(f"  ⏳  FloodWait – sleeping {e.seconds}s then retrying…")
            await asyncio.sleep(e.seconds)
            try:
                await client.forward_messages(dialog.entity, message_id, source_chat)
                print(f"  ✅  [{idx}/{total}]  {name}  (after flood wait)")
                success += 1
            except Exception as err:
                print(f"  ❌  [{idx}/{total}]  {name}  →  {err}")
                failed += 1
        except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError) as e:
            print(f"  ⛔  [{idx}/{total}]  {name}  →  {type(e).__name__}")
            failed += 1
        except Exception as e:
            print(f"  ❌  [{idx}/{total}]  {name}  →  {e}")
            failed += 1

        if idx < total:
            await asyncio.sleep(send_interval)

    return success, failed


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

async def main():
    global API_ID, API_HASH

    print("=" * 55)
    print("       Telegram Group Broadcaster")
    print("=" * 55)

    # ── Credentials ──────────────────────────
    if not API_ID or not API_HASH:
        print("\nℹ️  You need API credentials from https://my.telegram.org/apps\n")
        try:
            API_ID   = int(prompt("Enter your API ID   : "))
            API_HASH =     prompt("Enter your API HASH : ")
        except ValueError:
            print("❌  API ID must be a number.")
            sys.exit(1)

    # ── Connect & Login ───────────────────────
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"\n✔  Logged in as: {me.first_name} (@{me.username})")

    # ── Fetch groups ──────────────────────────
    print("\n⏳  Fetching all joined groups…")
    groups = await get_all_groups(client)
    print(f"✔  Found {len(groups)} group(s) / channel(s).\n")

    if not groups:
        print("No groups found. Exiting.")
        await client.disconnect()
        return

    # ── Choose mode ───────────────────────────
    print("Choose broadcast mode:")
    print("  1 → Send text message")
    print("  2 → Forward an existing message")
    mode = prompt("\nEnter 1 or 2 : ", "1")

    # ── Intervals ────────────────────────────
    print()
    try:
        send_interval = float(prompt("Send interval  – gap between each group send (seconds) [default 5]: ", "5"))
    except ValueError:
        send_interval = 5.0

    try:
        round_interval = float(prompt("Round interval – sleep after all groups are done (seconds) [default 3600]: ", "3600"))
    except ValueError:
        round_interval = 3600.0

    print(f"\n⏱  Send interval  : {send_interval}s  (per group)")
    print(f"🔄  Round interval : {fmt_seconds(round_interval)}  (after each full round)\n")

    # ── Mode-specific setup ───────────────────
    if mode == "1":
        print("Type / paste your message below.")
        print("(Type END on its own line to finish)\n")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        text = "\n".join(lines)

        if not text.strip():
            print("❌  Empty message. Exiting.")
            await client.disconnect()
            return

        print(f"\n📝  Message preview ({len(text)} chars):\n{'-'*40}\n{text}\n{'-'*40}")
        confirm = prompt("Send to all groups repeatedly? (yes/no) : ", "no")
        if confirm.lower() not in ("yes", "y"):
            print("Cancelled.")
            await client.disconnect()
            return

    elif mode == "2":
        print("To forward a message you need:")
        print("  • The username or ID of the chat that contains the message")
        print("  • The Message ID (right-click → Copy Message Link, last number in URL)\n")

        source = prompt("Source chat username or ID (e.g. @mychat or 123456): ")
        try:
            msg_id = int(prompt("Message ID to forward: "))
        except ValueError:
            print("❌  Message ID must be a number.")
            await client.disconnect()
            return

        try:
            source_entity = await client.get_entity(source)
        except Exception as e:
            print(f"❌  Could not resolve source chat: {e}")
            await client.disconnect()
            return

        confirm = prompt("\nForward to all groups repeatedly? (yes/no) : ", "no")
        if confirm.lower() not in ("yes", "y"):
            print("Cancelled.")
            await client.disconnect()
            return

    else:
        print("❌  Invalid choice.")
        await client.disconnect()
        return

    # ── Broadcast loop ────────────────────────
    round_num = 0
    try:
        while True:
            round_num += 1
            print(f"\n{'='*55}")
            print(f"  📣  ROUND {round_num}  —  {len(groups)} group(s)")
            print(f"{'='*55}\n")

            if mode == "1":
                success, failed = await broadcast_text(client, groups, text, send_interval)
            else:
                success, failed = await broadcast_forward(client, groups, source_entity, msg_id, send_interval)

            print(f"\n🏁  Round {round_num} complete — ✅ {success} sent, ❌ {failed} failed.")
            print(f"💤  Sleeping for {fmt_seconds(round_interval)} before next round…")

            await round_countdown(round_interval)

    except KeyboardInterrupt:
        print(f"\n\n⛔  Stopped by user after {round_num} round(s).")

    await client.disconnect()
    print("👋  Disconnected. Bye!")


if __name__ == "__main__":
    asyncio.run(main())
