#!/usr/bin/env python3
# main.py hotfix patcher for Pyrogram bot
#
# Fixes:
# 1. MESSAGE_NOT_MODIFIED crash from repeated edit_text()
# 2. FloodWait e.x issue -> e.value
# 3. time.sleep() inside async functions -> await asyncio.sleep()
# 4. missing global file_queue inside load_initial_data()
#
# Usage:
#   Put this file in your project root, then run:
#   python fix_main_hotpatch.py
#
# It patches:
#   Modules/main.py
#
# Backup created:
#   Modules/main.py.bak

from pathlib import Path
import re
import sys

TARGET = Path("Modules/main.py")

if not TARGET.exists():
    print("❌ Modules/main.py not found.")
    print("Put this file in your project root where Modules/main.py exists.")
    sys.exit(1)

text = TARGET.read_text(encoding="utf-8")

backup = TARGET.with_suffix(".py.bak")
backup.write_text(text, encoding="utf-8")
print(f"✅ Backup created: {backup}")

# Fix import
text = text.replace(
    "from pyrogram.errors import FloodWait",
    "from pyrogram.errors import FloodWait, MessageNotModified"
)

# Add safe_edit helper
helper_code = '''
\n
async def safe_edit(msg, text, reply_markup=None):
    """Safely edit Telegram messages without crashing on same-content edits."""
    try:
        return await msg.edit_text(
            text,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except MessageNotModified:
        return msg
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await safe_edit(msg, text, reply_markup)
    except Exception as e:
        logging.error(f"Edit failed: {e}")
        return msg
'''

if "async def safe_edit(" not in text:
    text = text.replace(
        "OWNER_IDS = [7448837918]  # Replace with the actual owner user IDs",
        "OWNER_IDS = [7448837918]  # Replace with the actual owner user IDs" + helper_code
    )

# Fix global file_queue
text = text.replace(
    "global total_running_time, max_running_time\n  ",
    "global total_running_time, max_running_time, file_queue\n  "
)

# Replace /start function
start_pattern = re.compile(
    r'@bot\.on_message\(filters\.command\("start"\)\)\s*async def start\(client: Client, msg: Message\):.*?(?=\n\n@bot\.on_message\(filters\.command\("stop"\)\))',
    re.S
)

new_start = '''@bot.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    start_message = await client.send_message(
        msg.chat.id,
        Data.START.format(msg.from_user.mention)
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(msg.from_user.mention) +
        "Initializing Uploader bot... 🤖\\n\\n"
        "Progress: [⬜⬜⬜⬜⬜⬜⬜⬜⬜] 0%\\n\\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(msg.from_user.mention) +
        "Loading features... ⏳\\n\\n"
        "Progress: [🟥🟥🟥⬜⬜⬜⬜⬜⬜] 25%\\n\\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(msg.from_user.mention) +
        "This may take a moment, sit back and relax! 😊\\n\\n"
        "Progress: [🟧🟧🟧🟧🟧⬜⬜⬜⬜] 50%\\n\\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(msg.from_user.mention) +
        "Checking subscription status... 🔍\\n\\n"
        "Progress: [🟨🟨🟨🟨🟨🟨🟨⬜⬜] 75%\\n\\n"
    )

    await asyncio.sleep(1)

    if msg.from_user.id in authorized_users:
        await safe_edit(
            start_message,
            Data.START.format(msg.from_user.mention) +
            "Great!, You are a premium member! 🌟 press `/help` in order to use me properly\\n\\n",
            reply_markup=help_button_keyboard
        )
    else:
        await asyncio.sleep(2)
        await safe_edit(
            start_message,
            Data.START.format(msg.from_user.mention) +
            "You are currently using the free version. 🆓\\n\\n"
            "I'm here to make your life easier by downloading videos from your **.txt** file 📄 and uploading them directly to Telegram!\\n\\n"
            "Want to get started? Press /id\\n\\n"
            "💬 Contact **[𝚉𝙴𝙽𝙸𝚃𝙷 🏅](https://t.me/ZenithOfficialhelp)** to Get The Subscription 🎫 and unlock the full potential of your new bot! 🔓"
        )'''

text, count = start_pattern.subn(new_start, text)

if count == 0:
    print("⚠️ Could not auto-replace /start function. Your file may be formatted differently.")
else:
    print("✅ /start function patched.")

# Replace blocking sleeps
text = text.replace("time.sleep(e.x)", "await asyncio.sleep(e.value)")
text = text.replace("time.sleep(3)", "await asyncio.sleep(3)")
text = text.replace("time.sleep(1)", "await asyncio.sleep(1)")

# Exception should be string
text = text.replace("await m.reply_text(e)", "await m.reply_text(str(e))")

TARGET.write_text(text, encoding="utf-8")
print("✅ Patch complete: Modules/main.py")
print("Now redeploy Railway/Render.")
