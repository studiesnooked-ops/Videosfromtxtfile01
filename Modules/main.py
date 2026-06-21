#!/usr/bin/env python3
# repair_main_force.py
#
# Strong repair for Modules/main.py
#
# Fixes:
# 1. Removes Git conflict markers: <<<<<<< ======= >>>>>>>
# 2. Removes broken /start command block
# 3. Adds clean /start command
# 4. Adds safe_edit if missing
# 5. Fixes FloodWait e.x -> e.value
# 6. Fixes time.sleep() inside async functions
# 7. Fixes await reply_text(e) -> str(e)
#
# Usage:
#   python repair_main_force.py

from pathlib import Path
import re
import sys
import datetime


TARGET = Path("Modules/main.py")

if not TARGET.exists():
    print("❌ Modules/main.py not found.")
    print("Put this file in your project root where Modules/main.py exists.")
    sys.exit(1)


text = TARGET.read_text(encoding="utf-8", errors="ignore")

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = TARGET.with_name(f"main.py.force_backup_{timestamp}")
backup.write_text(text, encoding="utf-8")
print(f"✅ Backup created: {backup}")


# =========================================================
# 1. Remove Git conflict blocks safely
# =========================================================

def score_conflict_side(side: list[str]) -> int:
    content = "\n".join(side)

    score = 0

    # Good bot-code signals
    good_words = [
        "@bot.on_message",
        "async def",
        "await ",
        "filters.command",
        "bot.run()",
        "reply_text",
        "send_message",
        "InlineKeyboard",
        "load_initial_data",
        "process_links",
        "process_file",
    ]

    # Bad patch-script signals
    bad_words = [
        "TARGET = Path",
        "TARGET.write_text",
        "start_pattern",
        "subn(",
        "Patch complete",
        "Backup created",
        "Could not auto-replace",
        "fix_main_hotpatch",
        "repair_main_force",
        "Path(",
        "sys.exit",
        "print(",
    ]

    for word in good_words:
        score += content.count(word) * 3

    for word in bad_words:
        score -= content.count(word) * 5

    if "Checking subscription status" in content:
        score += 20

    return score


def resolve_git_conflicts(src: str) -> str:
    lines = src.splitlines()
    out = []
    i = 0
    fixed = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("<<<<<<<"):
            fixed += 1
            i += 1

            left = []
            right = []
            current = left

            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                if lines[i].startswith("======="):
                    current = right
                else:
                    current.append(lines[i])
                i += 1

            # Skip >>>>>>>
            if i < len(lines) and lines[i].startswith(">>>>>>>"):
                i += 1

            left_score = score_conflict_side(left)
            right_score = score_conflict_side(right)

            chosen = right if right_score >= left_score else left
            out.extend(chosen)
            continue

        # Remove loose conflict marker lines
        if line.startswith("=======") or line.startswith(">>>>>>>"):
            i += 1
            continue

        out.append(line)
        i += 1

    if fixed:
        print(f"✅ Resolved {fixed} Git conflict block(s).")
    else:
        print("ℹ️ No full Git conflict block found.")

    return "\n".join(out) + "\n"


text = resolve_git_conflicts(text)


# =========================================================
# 2. Remove accidental patcher code if it entered main.py
# =========================================================

bad_markers = [
    "text, count = start_pattern.subn",
    "TARGET.write_text(text",
    "print(\"✅ Patch complete",
    "print(\"Now redeploy",
    "print(\"✅ Now run:",
]

for marker in bad_markers:
    pos = text.find(marker)
    if pos != -1:
        print(f"⚠️ Removed accidental patcher code starting from: {marker}")
        text = text[:pos].rstrip() + "\n"
        break


# =========================================================
# 3. Fix import for MessageNotModified
# =========================================================

if "from pyrogram.errors import FloodWait" in text and "MessageNotModified" not in text:
    text = text.replace(
        "from pyrogram.errors import FloodWait",
        "from pyrogram.errors import FloodWait, MessageNotModified"
    )

text = text.replace(
    "from pyrogram.errors import FloodWait, MessageNotModified, MessageNotModified",
    "from pyrogram.errors import FloodWait, MessageNotModified"
)


# =========================================================
# 4. Add safe_edit helper if missing
# =========================================================

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
    owner_line = re.search(r"^OWNER_IDS\s*=\s*\[[^\n]*\].*$", text, flags=re.M)

    if owner_line:
        insert_pos = owner_line.end()
        text = text[:insert_pos] + helper_code + text[insert_pos:]
        print("✅ safe_edit helper added after OWNER_IDS.")
    else:
        marker = '@bot.on_message(filters.command("start"))'
        pos = text.find(marker)
        if pos != -1:
            text = text[:pos] + helper_code + "\n" + text[pos:]
            print("✅ safe_edit helper added before /start.")
        else:
            text = helper_code + "\n" + text
            print("✅ safe_edit helper added at top fallback.")
else:
    print("ℹ️ safe_edit already exists.")


# =========================================================
# 5. Force replace /start command
# =========================================================

clean_start = r'''@bot.on_message(filters.command("start"))
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
        )
'''


start_decorator_patterns = [
    '@bot.on_message(filters.command("start"))',
    "@bot.on_message(filters.command('start'))",
]

stop_decorator_patterns = [
    '@bot.on_message(filters.command("stop"))',
    "@bot.on_message(filters.command('stop'))",
]

start_pos = -1
for p in start_decorator_patterns:
    start_pos = text.find(p)
    if start_pos != -1:
        break

stop_pos = -1
for p in stop_decorator_patterns:
    stop_pos = text.find(p)
    if stop_pos != -1:
        break

if start_pos != -1 and stop_pos != -1 and stop_pos > start_pos:
    text = text[:start_pos] + clean_start + "\n\n" + text[stop_pos:]
    print("✅ /start function force replaced.")
else:
    print("⚠️ Could not find normal /start to /stop block.")
    print("⚠️ Trying regex fallback...")

    start_regex = re.compile(
        r'@bot\.on_message\(filters\.command\(["\']start["\']\)\)\s*'
        r'async\s+def\s+start\(.*?\):.*?'
        r'(?=\n\s*@bot\.on_message)',
        re.S
    )

    text, replaced = start_regex.subn(clean_start + "\n\n", text, count=1)

    if replaced:
        print("✅ /start function replaced by regex fallback.")
    else:
        # Add clean start before first stop handler if possible
        if stop_pos != -1:
            text = text[:stop_pos] + clean_start + "\n\n" + text[stop_pos:]
            print("✅ Clean /start inserted before /stop.")
        else:
            print("❌ Could not locate place for /start.")
            print("❌ Please send your Modules/main.py file if this still fails.")


# =========================================================
# 6. Fix global file_queue inside load_initial_data
# =========================================================

text = re.sub(
    r"global\s+total_running_time\s*,\s*max_running_time(?!\s*,\s*file_queue)",
    "global total_running_time, max_running_time, file_queue",
    text
)


# =========================================================
# 7. Fix async sleeps and FloodWait
# =========================================================

text = text.replace("time.sleep(e.x)", "await asyncio.sleep(e.value)")
text = text.replace("time.sleep(e.value)", "await asyncio.sleep(e.value)")
text = text.replace("time.sleep(10)", "await asyncio.sleep(10)")
text = text.replace("time.sleep(5)", "await asyncio.sleep(5)")
text = text.replace("time.sleep(3)", "await asyncio.sleep(3)")
text = text.replace("time.sleep(2)", "await asyncio.sleep(2)")
text = text.replace("time.sleep(1)", "await asyncio.sleep(1)")

text = text.replace("await m.reply_text(e)", "await m.reply_text(str(e))")
text = text.replace("await message.reply_text(e)", "await message.reply_text(str(e))")


# =========================================================
# 8. Final check
# =========================================================

if "<<<<<<<" in text or "=======" in text or ">>>>>>>" in text:
    print("❌ Some conflict markers still remain.")
    print("❌ Open Modules/main.py and search for: <<<<<<<")
    print("❌ Delete the conflict block manually.")
else:
    print("✅ No Git conflict markers remain.")


TARGET.write_text(text, encoding="utf-8")

print("✅ Strong repair complete: Modules/main.py")
print("")
print("Now test syntax with:")
print("python -m py_compile Modules/main.py")
print("")
print("Then run bot:")
print("python Modules/main.py")
