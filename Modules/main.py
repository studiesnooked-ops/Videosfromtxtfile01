#!/usr/bin/env python3
# fix_main_hotpatch.py
#
# Hotfix patcher for Pyrogram bot main.py
#
# Fixes:
# 1. MESSAGE_NOT_MODIFIED crash from repeated edit_text()
# 2. FloodWait e.x issue -> e.value
# 3. time.sleep() inside async functions -> await asyncio.sleep()
# 4. missing global file_queue inside load_initial_data()
# 5. broken /start command conflict code
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


# ---------------------------------------------------------
# 1. Fix Pyrogram error imports
# ---------------------------------------------------------

if "MessageNotModified" not in text:
    text = text.replace(
        "from pyrogram.errors import FloodWait",
        "from pyrogram.errors import FloodWait, MessageNotModified"
    )

# If import line already changed badly, clean duplicate imports
text = text.replace(
    "from pyrogram.errors import FloodWait, MessageNotModified, MessageNotModified",
    "from pyrogram.errors import FloodWait, MessageNotModified"
)


# ---------------------------------------------------------
# 2. Add safe_edit helper
# ---------------------------------------------------------

helper_code = r'''


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
    owner_pattern = re.compile(r'^(OWNER_IDS\s*=\s*\[[^\n]*\].*)$', re.M)

    if owner_pattern.search(text):
        text = owner_pattern.sub(r'\1' + helper_code, text, count=1)
        print("✅ safe_edit helper added after OWNER_IDS.")
    else:
        # Fallback: add before /start handler
        start_marker = '@bot.on_message(filters.command("start"))'
        if start_marker in text:
            text = text.replace(start_marker, helper_code + "\n" + start_marker, 1)
            print("✅ safe_edit helper added before /start.")
        else:
            print("⚠️ Could not find OWNER_IDS or /start marker. safe_edit not inserted.")
else:
    print("ℹ️ safe_edit already exists.")


# ---------------------------------------------------------
# 3. Fix missing global file_queue inside load_initial_data()
# ---------------------------------------------------------

text = re.sub(
    r'global\s+total_running_time\s*,\s*max_running_time(?!\s*,\s*file_queue)',
    'global total_running_time, max_running_time, file_queue',
    text
)


# ---------------------------------------------------------
# 4. Replace /start command safely
# ---------------------------------------------------------

start_pattern = re.compile(
    r'@bot\.on_message\(filters\.command\(["\']start["\']\)\)\s*'
    r'async\s+def\s+start\(.*?\):.*?'
    r'(?=\n\s*@bot\.on_message\(filters\.command\(["\']stop["\']\)\))',
    re.S
)

new_start = r'''@bot.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    user_mention = msg.from_user.mention if msg.from_user else "User"

    start_message = await client.send_message(
        msg.chat.id,
        Data.START.format(user_mention)
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(user_mention) +
        "Initializing Uploader bot... 🤖\n\n"
        "Progress: [⬜⬜⬜⬜⬜⬜⬜⬜⬜] 0%\n\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(user_mention) +
        "Loading features... ⏳\n\n"
        "Progress: [🟥🟥🟥⬜⬜⬜⬜⬜⬜] 25%\n\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(user_mention) +
        "This may take a moment, please relax! 😊\n\n"
        "Progress: [🟧🟧🟧🟧🟧⬜⬜⬜⬜] 50%\n\n"
    )

    await asyncio.sleep(1)
    await safe_edit(
        start_message,
        Data.START.format(user_mention) +
        "Checking subscription status... 🔍\n\n"
        "Progress: [🟨🟨🟨🟨🟨🟨🟨⬜⬜] 75%\n\n"
    )

    await asyncio.sleep(1)

    if msg.from_user and msg.from_user.id in authorized_users:
        await safe_edit(
            start_message,
            Data.START.format(user_mention) +
            "Great! You are a premium member! 🌟\n\n"
            "Press /help to use me properly.\n\n",
            reply_markup=help_button_keyboard
        )
    else:
        await asyncio.sleep(2)
        await safe_edit(
            start_message,
            Data.START.format(user_mention) +
            "You are currently using the free version. 🆓\n\n"
            "I'm here to make your life easier by downloading videos from your .txt file 📄 "
            "and uploading them directly to Telegram!\n\n"
            "Want to get started? Press /id\n\n"
            "💬 Contact **[𝚉𝙴𝙽𝙸𝚃𝙷 🏅](https://t.me/ZenithOfficialhelp)** "
            "to get the subscription 🎫 and unlock the full bot."
        )'''

text, replaced = start_pattern.subn(new_start, text)

if replaced == 0:
    print("⚠️ Could not auto-replace /start function. Your file may be formatted differently.")
else:
    print("✅ /start function patched.")


# ---------------------------------------------------------
# 5. Replace blocking sleep calls
# ---------------------------------------------------------

text = text.replace("time.sleep(e.x)", "await asyncio.sleep(e.value)")
text = text.replace("time.sleep(e.value)", "await asyncio.sleep(e.value)")
text = text.replace("time.sleep(3)", "await asyncio.sleep(3)")
text = text.replace("time.sleep(2)", "await asyncio.sleep(2)")
text = text.replace("time.sleep(1)", "await asyncio.sleep(1)")


# ---------------------------------------------------------
# 6. Fix reply_text exception object
# ---------------------------------------------------------

text = text.replace("await m.reply_text(e)", "await m.reply_text(str(e))")
text = text.replace("await message.reply_text(e)", "await message.reply_text(str(e))")


# ---------------------------------------------------------
# 7. Remove accidental Git conflict markers if present
# ---------------------------------------------------------

if "<<<<<<<" in text or ">>>>>>>" in text or "=======" in text:
    print("⚠️ Git conflict markers found in Modules/main.py.")
    print("⚠️ Please manually remove lines containing <<<<<<<, =======, >>>>>>> if bot fails.")
    print("⚠️ This patcher does not auto-resolve full Git conflicts to avoid deleting your code.")


# ---------------------------------------------------------
# 8. Write patched file
# ---------------------------------------------------------

TARGET.write_text(text, encoding="utf-8")

print("✅ Patch complete: Modules/main.py")
print("✅ Now run:")
print("   python Modules/main.py")
print("")
print("✅ Or redeploy Railway/Render.")
