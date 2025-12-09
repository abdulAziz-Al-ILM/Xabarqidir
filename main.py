import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.builtin import Command
import sqlite3

# --- Konfiguratsiya ---
API_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID') # Bot monitoring xabarlarini yuboradigan admin ID si

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- Ma'lumotlar bazasi (DB) ---
DB_NAME = 'monitor_words.db'

def init_db():
    """Ma'lumotlar bazasini va 'words' jadvalini yaratadi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            word TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_word_to_db(word):
    """Yangi so'zni ma'lumotlar bazasiga qo'shadi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO words (word) VALUES (?)", (word.lower(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # So'z allaqachon mavjud
    finally:
        conn.close()

def get_all_words():
    """Barcha maxsus so'zlarni oladi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words

def remove_word_from_db(word):
    """So'zni ma'lumotlar bazasidan o'chiradi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE word = ?", (word.lower(),))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count > 0

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

