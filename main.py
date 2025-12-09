import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- SOZLAMALAR ---
# Railway Environment Variables dan o'qib oladi
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # Sizning ID raqamingiz (string ko'rinishida kelishi mumkin)

# Loglarni yoqish
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- BAZA BILAN ISHLASH (SQLite) ---
def db_connect():
    conn = sqlite3.connect("words.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bad_words (
            word TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    return conn

def add_word(word):
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO bad_words (word) VALUES (?)", (word.lower(),))
        conn.commit()
        status = True
    except sqlite3.IntegrityError:
        status = False
    conn.close()
    return status

def get_words():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM bad_words")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words

def delete_word(word):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bad_words WHERE word = ?", (word.lower(),))
    conn.commit()
    conn.close()

# --- ADMIN BUYRUQLARI ---

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Men guruhdagi so'zlarni nazorat qiluvchi botman.\n"
                        "Buyruqlar (faqat admin uchun):\n"
                        "/add <so'z> - So'z qo'shish\n"
                        "/del <so'z> - So'zni o'chirish\n"
                        "/list - Ro'yxatni ko'rish")

@dp.message_handler(commands=['add'])
async def add_new_word(message: types.Message):
    # Faqat admin ishlata olsin
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    args = message.get_args()
    if not args:
        await message.reply("So'zni kiriting. Masalan: /add non")
        return

    word = args.lower().strip()
    if add_word(word):
        await message.reply(f"✅ '{word}' so'zi nazorat ro'yxatiga qo'shildi.")
    else:
        await message.reply(f"⚠️ '{word}' so'zi allaqachon mavjud.")

@dp.message_handler(commands=['del'])
async def remove_existing_word(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    args = message.get_args()
    if not args:
        await message.reply("O'chirish uchun so'z kiriting. Masalan: /del non")
        return

    word = args.lower().strip()
    delete_word(word)
    await message.reply(f"🗑 '{word}' so'zi ro'yxatdan o'chirildi.")

@dp.message_handler(commands=['list'])
async def list_all_words(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    words = get_words()
    if words:
        text = "📋 **Nazoratdagi so'zlar:**\n\n" + "\n".join(words)
    else:
        text = "Ro'yxat bo'sh."
    await message.reply(text, parse_mode="Markdown")

# --- GURUH XABARLARINI TEKSHIRISH ---

@dp.message_handler(content_types=['text'])
async def check_messages(message: types.Message):
    # Agar xabar guruhdan bo'lsa
    if message.chat.type in ['group', 'supergroup']:
        text = message.text.lower()
        words = get_words()
        
        found_word = None
        for word in words:
            # Oddiy qidiruv (so'z ichida bo'lsa ham topadi)
            if word in text:
                found_word = word
                break
        
        if found_word:
            user = message.from_user
            chat = message.chat
            
            # Xabar linkini yasash (superguruhlar uchun)
            msg_link = f"https://t.me/c/{str(chat.id)[4:]}/{message.message_id}"
            
            report = (
                f"🚨 **Diqqat! Taqiqlangan so'z topildi.**\n\n"
                f"🗝 **So'z:** {found_word}\n"
                f"👤 **Foydalanuvchi:** {user.full_name}\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"📧 **Username:** @{user.username if user.username else 'Yo\'q'}\n"
                f"📍 **Guruh:** {chat.title}\n\n"
                f"📄 **Xabar matni:**\n{message.text}\n\n"
                f"🔗 [Xabarga o'tish]({msg_link})"
            )
            
            # Adminga xabar yuborish
            try:
                await bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode="Markdown")
            except Exception as e:
                print(f"Adminga yuborishda xatolik: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

# --- Admin Buyruqlari (Guruhda) ---

@dp.message_handler(Command('start', prefixes=['/']))
async def send_welcome(message: types.Message):
    """/start buyrug'ini ushlaydi."""
    await message.reply("Salom! Men guruhdagi maxsus so'zlarni kuzatuvchi botman. Faqat adminlar foydalana oladigan buyruqlar: /addword, /listwords, /delword.")

@dp.message_handler(Command('addword', prefixes=['/']))
async def add_word_command(message: types.Message):
    """/addword <so'z> - Yangi maxsus so'z qo'shish."""
    if str(message.from_user.id) != ADMIN_ID:
        await message.reply("Kechirasiz, bu buyruq faqat bot admini uchun.")
        return

    args = message.get_args().strip()
    if not args:
        await message.reply("Qo'shiladigan so'zni kiriting. Format: `/addword <so'z>`")
        return

    word_to_add = args.split()[0].lower() # Faqat birinchi so'zni olamiz
    if add_word_to_db(word_to_add):
        await message.reply(f"✅ Maxsus so'z qo'shildi: **{word_to_add}**")
    else:
        await message.reply(f"❌ So'z allaqachon mavjud: **{word_to_add}**")

@dp.message_handler(Command('listwords', prefixes=['/']))
async def list_words_command(message: types.Message):
    """/listwords - Barcha maxsus so'zlar ro'yxatini ko'rish."""
    if str(message.from_user.id) != ADMIN_ID:
        await message.reply("Kechirasiz, bu buyruq faqat bot admini uchun.")
        return

    words = get_all_words()
    if words:
        word_list = "\n".join([f"* {w}" for w in words])
        await message.reply(f"📝 **Kuzatilayotgan maxsus so'zlar ro'yxati:**\n\n{word_list}")
    else:
        await message.reply("Ro'yxat bo'sh. Hech qanday maxsus so'z kuzatilmayapti.")

@dp.message_handler(Command('delword', prefixes=['/']))
async def del_word_command(message: types.Message):
    """/delword <so'z> - Maxsus so'zni o'chirish."""
    if str(message.from_user.id) != ADMIN_ID:
        await message.reply("Kechirasiz, bu buyruq faqat bot admini uchun.")
        return

    args = message.get_args().strip()
    if not args:
        await message.reply("O'chiriladigan so'zni kiriting. Format: `/delword <so'z>`")
        return

    word_to_remove = args.split()[0].lower()
    if remove_word_from_db(word_to_remove):
        await message.reply(f"🗑️ Maxsus so'z o'chirildi: **{word_to_remove}**")
    else:
        await message.reply(f"❌ So'z ro'yxatda mavjud emas: **{word_to_remove}**")


# --- Xabarlarni Kuzatish Mantiqi (Guruhdagi har bir xabar uchun) ---

@dp.message_handler(content_types=types.ContentType.TEXT)
async def monitor_messages(message: types.Message):
    """Guruhdagi har bir matnli xabarni tekshiradi."""
    
    # Guruhda ekanligiga ishonch hosil qilish
    if message.chat.type in [types.ChatType.GROUP, types.ChatType.SUPERGROUP]:
        
        message_text = message.text.lower()
        monitored_words = get_all_words()
        
        found_words = []
        for word in monitored_words:
            if word in message_text:
                found_words.append(word)
        
        if found_words:
            # So'z topildi, adminni xabardor qilish
            
            # Xabar muallifi ma'lumotlari
            user = message.from_user
            username = f"@{user.username}" if user.username else "mavjud emas"
            full_name = user.full_name
            user_id = user.id
            
            # Xabar yuborilgan guruh ma'lumotlari
            chat_title = message.chat.title
            
            # Xabarni admin uchun formatlash
            report_message = (
                "🚨 **Maxsus so'z topildi!** 🚨\n\n"
                f"**Guruh:** {chat_title}\n"
                f"**Topilgan so'z(lar):** {', '.join(found_words)}\n"
                f"**Yozuvchi:** [{full_name}](tg://user?id={user_id})\n"
                f"**Username:** `{username}`\n"
                f"**User ID:** `{user_id}`\n\n"
                f"**Original xabar:**\n"
                "> {message.text}"
            )

            try:
                # Xabarni adminda yuborish
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=report_message,
                    parse_mode=types.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                
                # Agar admin xohlasa, original xabarga link ham yuborish mumkin
                message_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"[Original xabarga o'tish]({message_link})",
                    parse_mode=types.ParseMode.MARKDOWN
                )
                
            except Exception as e:
                logging.error(f"Adminga xabar yuborishda xato: {e}")


# --- Asosiy ishga tushirish qismi ---

if __name__ == '__main__':
    if not API_TOKEN or not ADMIN_ID:
        logging.error("BOT_TOKEN va ADMIN_ID muhit o'zgaruvchilari o'rnatilmagan.")
    else:
        init_db() # DB ni ishga tushirish
        logging.info("Bot ishga tushirildi.")
        # Botni ishga tushirish (uzoq so'rovlar rejimida)
        executor.start_polling(dp, skip_updates=True)

