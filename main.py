import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold, hcode

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Faylga asoslangan kalit so'zlarni saqlash
KEYWORDS_FILE = "keywords.json"

def load_keywords():
    """Kalit so'zlarni fayldan yuklaydi."""
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_keywords(keywords):
    """Kalit so'zlarni faylga saqlaydi."""
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(keywords), f, ensure_ascii=False, indent=4)

# Global kalit so'zlar to'plami
MONITORED_KEYWORDS = load_keywords()

# Environment o'zgaruvchilari
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Adminning chat IDsi (integer)

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment o'zgaruvchisi topilmadi.")
    exit(1)
if not ADMIN_ID:
    logger.warning("ADMIN_ID environment o'zgaruvchisi topilmadi. Admin buyruqlari ishlamasligi mumkin.")
    ADMIN_ID = None
else:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        logger.error("ADMIN_ID noto'g'ri formatda. Integer bo'lishi kerak.")
        exit(1)

# --- Handlerlar ---

async def is_admin(message: Message) -> bool:
    """Xabar yuboruvchining admin ekanligini tekshiradi."""
    if ADMIN_ID is None:
        return False
    return message.from_user.id == ADMIN_ID

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """/start buyrug'iga javob beradi."""
    await message.answer(f"Salom, {hbold(message.from_user.full_name)}! Men guruhlarda maxsus so'zlarni kuzatuvchi botman.")
    if await is_admin(message):
        await message.answer("Siz adminsiz. Kalit so'zlarni boshqarish uchun /add_word, /remove_word, /list_words buyruqlaridan foydalanishingiz mumkin.")

@dp.message(Command("add_word"))
async def add_word_handler(message: Message) -> None:
    """Kalit so'z qo'shish buyrug'i."""
    if not await is_admin(message):
        return await message.answer("Sizda bu buyruqni ishlatishga ruxsat yo'q.")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Foydalanish: /add_word <so'z>")

    word = args[1].strip().lower()
    if not word:
        return await message.answer("So'z bo'sh bo'lishi mumkin emas.")

    if word in MONITORED_KEYWORDS:
        return await message.answer(f"'{word}' so'zi allaqachon ro'yxatda mavjud.")

    MONITORED_KEYWORDS.add(word)
    save_keywords(MONITORED_KEYWORDS)
    await message.answer(f"'{word}' so'zi muvaffaqiyatli qo'shildi.")
    logger.info(f"Admin {message.from_user.id} tomonidan '{word}' so'zi qo'shildi.")

@dp.message(Command("remove_word"))
async def remove_word_handler(message: Message) -> None:
    """Kalit so'zni olib tashlash buyrug'i."""
    if not await is_admin(message):
        return await message.answer("Sizda bu buyruqni ishlatishga ruxsat yo'q.")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Foydalanish: /remove_word <so'z>")

    word = args[1].strip().lower()
    if word not in MONITORED_KEYWORDS:
        return await message.answer(f"'{word}' so'zi ro'yxatda mavjud emas.")

    MONITORED_KEYWORDS.remove(word)
    save_keywords(MONITORED_KEYWORDS)
    await message.answer(f"'{word}' so'zi muvaffaqiyatli olib tashlandi.")
    logger.info(f"Admin {message.from_user.id} tomonidan '{word}' so'zi olib tashlandi.")

@dp.message(Command("list_words"))
async def list_words_handler(message: Message) -> None:
    """Kalit so'zlar ro'yxatini ko'rsatish buyrug'i."""
    if not await is_admin(message):
        return await message.answer("Sizda bu buyruqni ishlatishga ruxsat yo'q.")

    if not MONITORED_KEYWORDS:
        return await message.answer("Kuzatilayotgan kalit so'zlar mavjud emas.")

    words_list = "\n".join(sorted(list(MONITORED_KEYWORDS)))
    await message.answer(f"{hbold('Kuzatilayotgan kalit so\'zlar:')}\n{hcode(words_list)}")

@dp.message(F.text | F.caption)
async def monitor_messages(message: Message, bot: Bot) -> None:
    """Guruh xabarlarini kuzatish va kalit so'z topilsa adminga xabar berish."""
    if not MONITORED_KEYWORDS:
        return # Kalit so'zlar bo'lmasa, tekshirish shart emas

    # Faqat guruh yoki superguruhlarda ishlaymiz
    if message.chat.type not in ["group", "supergroup"]:
        return

    text_to_check = (message.text or message.caption or "").lower()
    
    found_word = None
    for word in MONITORED_KEYWORDS:
        # So'zni butun so'z sifatida yoki matnning bir qismi sifatida qidirish
        # Hozircha oddiy qidiruvni ishlatamiz, chunki foydalanuvchi butun so'z talabini aytmadi.
        if word in text_to_check:
            found_word = word
            break

    if found_word and ADMIN_ID:
        user = message.from_user
        chat = message.chat
        
        # Xabar yuboruvchi ma'lumotlari
        user_info = (
            f"Foydalanuvchi ID: {hcode(user.id)}\n"
            f"Username: @{user.username}" if user.username else f"Username: Mavjud emas\n"
            f"To'liq ism: {hbold(user.full_name)}"
        )
        
        # Guruh ma'lumotlari
        chat_info = (
            f"Guruh ID: {hcode(chat.id)}\n"
            f"Guruh nomi: {hbold(chat.title)}"
        )
        
        # Adminga yuboriladigan xabar matni
        report_text = (
            f"{hbold('!!! MAXSUS SO\'Z TOPILDI !!!')}\n\n"
            f"Topilgan so'z: {hbold(found_word)}\n\n"
            f"{chat_info}\n\n"
            f"{user_info}\n\n"
            f"{hbold('Asl xabar:')}"
        )
        
        # Adminga xabar yuborish
        try:
            await bot.send_message(ADMIN_ID, report_text)
            # Asl xabarni adminga forward qilish
            await message.forward(ADMIN_ID)
            logger.info(f"Kalit so'z topildi: '{found_word}'. Xabar adminga ({ADMIN_ID}) yuborildi.")
        except Exception as e:
            logger.error(f"Adminga xabar yuborishda xato: {e}")


async def main() -> None:
    """Botni ishga tushirish."""
    global dp
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    
    # Handlerlarni ro'yxatdan o'tkazish
    dp.message.register(command_start_handler, CommandStart())
    dp.message.register(add_word_handler, Command("add_word"))
    dp.message.register(remove_word_handler, Command("remove_word"))
    dp.message.register(list_words_handler, Command("list_words"))
    dp.message.register(monitor_messages, F.text | F.caption) # Matnli yoki sarlavhali xabarlarni kuzatish

    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
