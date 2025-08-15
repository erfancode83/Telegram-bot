from telethon.sync import TelegramClient
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError
import asyncio
import sqlite3
import random

# ==================== تنظیمات شما ====================
API_ID = 26712608  # جایگزین کنید (از my.telegram.org)
API_HASH = '5815f68ea3da8a717889ad3f49f9c2c6'  # جایگزین کنید (از my.telegram.org)
PHONE = '+989922541200'  # جایگزین کنید (با پیش‌شماره کشور)
AUTHORIZED_USERS = {7747822781}  # آی‌دی شما (از @userinfobot دریافت شود)
# ====================================================

# Initialize Telegram client
client = TelegramClient('session', API_ID, API_HASH)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_users (
            username TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

init_db()

async def join_groups():
    """Join all groups from the database."""
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM groups')
    groups = cursor.fetchall()
    conn.close()

    for group in groups:
        try:
            await client(JoinChannelRequest(group[0]))
            print(f"✅ Joined: {group[0]}")
        except Exception as e:
            print(f"❌ Failed to join {group[0]}: {e}")

async def send_to_group_members():
    """Send random messages to group members with rate limiting."""
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username FROM groups')
    groups = cursor.fetchall()
    cursor.execute('SELECT text FROM messages')
    messages = [msg[0] for msg in cursor.fetchall()]

    if not groups or not messages:
        print("⛔ No groups or messages found!")
        return

    semaphore = asyncio.Semaphore(5)  # Limit concurrent sends

    async def send_message(user, msg):
        async with semaphore:
            try:
                if user.bot or not getattr(user, 'username', None):
                    return
                if cursor.execute('SELECT username FROM sent_users WHERE username=?', (user.username,)).fetchone():
                    return

                await client.send_message(user.username, msg)
                cursor.execute('INSERT INTO sent_users VALUES (?)', (user.username,))
                conn.commit()
                print(f"📤 Sent to: {user.username}")
                await asyncio.sleep(random.randint(5, 10))
            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Error sending to {user.username}: {e}")

    for group in groups:
        try:
            target_group = await client.get_entity(group[0])
            async for user in client.iter_participants(target_group):
                await send_message(user, random.choice(messages))
        except Exception as e:
            print(f"❌ Error in group {group[0]}: {e}")

    conn.close()

# Command handlers
@client.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    await event.respond(
        "🤖 **دستورات ربات:**\n\n"
        "📌 مدیریت گروه:\n"
        "/addgroup [یوزرنیم]\n"
        "/delgroup [یوزرنیم]\n"
        "/showgroups\n\n"
        "📌 مدیریت پیام:\n"
        "/addmsg [متن]\n"
        "/delmsg [متن]\n"
        "/showmsgs\n\n"
        "🚀 /startsend - آغاز ارسال"
    )

@client.on(events.NewMessage(pattern='/addgroup (.+)'))
async def add_group(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    group = event.pattern_match.group(1)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO groups (username) VALUES (?)', (group,))
        conn.commit()
        await event.respond(f"✅ گروه {group} اضافه شد")
    except sqlite3.IntegrityError:
        await event.respond("⚠️ گروه تکراری است")
    conn.close()

@client.on(events.NewMessage(pattern='/delgroup (.+)'))
async def del_group(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    group = event.pattern_match.group(1)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM groups WHERE username=?', (group,))
    conn.commit()
    if cursor.rowcount > 0:
        await event.respond(f"✅ گروه {group} حذف شد")
    else:
        await event.respond("⛔ گروه یافت نشد")
    conn.close()

@client.on(events.NewMessage(pattern='/addmsg (.+)'))
async def add_msg(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    msg = event.pattern_match.group(1)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO messages (text) VALUES (?)', (msg,))
        conn.commit()
        await event.respond("✅ پیام ذخیره شد")
    except sqlite3.IntegrityError:
        await event.respond("⚠️ پیام تکراری است")
    conn.close()

@client.on(events.NewMessage(pattern='/delmsg (.+)'))
async def del_msg(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    msg = event.pattern_match.group(1)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE text=?', (msg,))
    conn.commit()
    if cursor.rowcount > 0:
        await event.respond(f"✅ پیام حذف شد")
    else:
        await event.respond("⛔ پیام یافت نشد")
    conn.close()

@client.on(events.NewMessage(pattern='/showgroups'))
async def show_groups(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM groups')
    groups = cursor.fetchall()
    conn.close()
    await event.respond("📚 گروه‌ها:\n" + "\n".join(g[0] for g in groups) if groups else "📭 لیست خالی است")

@client.on(events.NewMessage(pattern='/showmsgs'))
async def show_msgs(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT text FROM messages')
    msgs = cursor.fetchall()
    conn.close()
    await event.respond("✉️ پیام‌ها:\n" + "\n".join(m[0] for m in msgs) if msgs else "📭 لیست خالی است")

@client.on(events.NewMessage(pattern='/startsend'))
async def start_send(event):
    if event.sender_id not in AUTHORIZED_USERS:
        return
    await event.respond("⏳ آغاز ارسال...")
    asyncio.create_task(send_to_group_members())
    await event.respond("✅ ارسال در پس‌زمینه آغاز شد")

with client:
    client.loop.run_until_complete(join_groups())
    client.run_until_disconnected()