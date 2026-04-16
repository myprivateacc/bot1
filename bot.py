"""
Telegram Group Broadcaster
---------------------------
Login with your Telegram account and broadcast a text message
OR forward an existing message to every group you have joined.

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
API_HASH = fb46a136fed4a4de27ab057c7027fec3   # e.g. "abcdef1234567890abcdef1234567890"

SESSION_NAME = "tg_broadcaster"


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


async def get_all_groups(client) -> list:
    """Return every dialog that is a group or supergroup/channel."""
    groups = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        # Skip forbidden / unavailable entities
        if isinstance(entity, (ChatForbidden, ChannelForbidden)):
            continue
        if isinstance(entity, Chat):
            groups.append(dialog)
        elif isinstance(entity, Channel) and (entity.megagroup or entity.broadcast is False):
            groups.append(dialog)
        elif isinstance(entity, Channel):
            # Include broadcast channels too (user may want them)
            groups.append(dialog)
    return groups


async def broadcast_text(client, groups: list, text: str, interval: float):
    """Send a text message to every group with the given interval (seconds)."""
    total   = len(groups)
    success = 0
    failed  = 0

    print(f"\n📤  Starting broadcast to {total} group(s)…\n")

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
            await asyncio.sleep(interval)

    print(f"\n🏁  Done — {success} sent, {failed} failed out of {total} groups.")


async def broadcast_forward(client, groups: list, source_chat, message_id: int, interval: float):
    """Forward a specific message to every group."""
    total   = len(groups)
    success = 0
    failed  = 0

    print(f"\n📤  Starting forward to {total} group(s)…\n")

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
            await asyncio.sleep(interval)

    print(f"\n🏁  Done — {success} forwarded, {failed} failed out of {total} groups.")


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
    await client.start()          # prompts for phone / OTP / 2FA if needed
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

    # ── Interval ─────────────────────────────
    try:
        interval = float(prompt("Interval between each send (seconds) [default 5]: ", "5"))
    except ValueError:
        interval = 5.0
    print(f"⏱  Interval set to {interval}s")

    # ── Mode 1 : Text ─────────────────────────
    if mode == "1":
        print("\nType / paste your message below.")
        print("(Enter a blank line followed by END on its own line to finish)\n")
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
        confirm = prompt("Send to all groups? (yes/no) : ", "no")
        if confirm.lower() not in ("yes", "y"):
            print("Cancelled.")
            await client.disconnect()
            return

        await broadcast_text(client, groups, text, interval)

    # ── Mode 2 : Forward ──────────────────────
    elif mode == "2":
        print("\nTo forward a message you need:")
        print("  • The username or ID of the chat that contains the message")
        print("  • The Message ID (right-click a message → Copy Message Link,")
        print("    the last number in the URL is the message ID)\n")

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

        confirm = prompt("\nForward to all groups? (yes/no) : ", "no")
        if confirm.lower() not in ("yes", "y"):
            print("Cancelled.")
            await client.disconnect()
            return

        await broadcast_forward(client, groups, source_entity, msg_id, interval)

    else:
        print("❌  Invalid choice.")

    await client.disconnect()
    print("\n👋  Disconnected. Bye!")


if __name__ == "__main__":
    asyncio.run(main())
