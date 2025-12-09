import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from functools import wraps

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Maxsus so'zlarni saqlash uchun lug'at. Kalit: chat ID, Qiymat: so'zlar ro'yxati
monitored_words = {}

# Guruh adminligini tekshirish uchun dekorator
def restricted_to_admin(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type in ["group", "supergroup"]:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Guruh a'zolarini olish va adminlikni tekshirish
            try:
                chat_members = await context.bot.get_chat_administrators(chat_id)
                admin_ids = [member.user.id for member in chat_members]
                
                if user_id not in admin_ids:
                    await update.message.reply_text("Kechirasiz, bu buyruq faqat guruh **administratorlari** uchun!")
                    return
            except Exception as e:
                logger.error(f"Admin tekshiruvi xatosi: {e}")
                await update.message.reply_text("Adminlikni tekshirishda xatolik yuz berdi. Iltimos, botning admin ekanligiga ishonch hosil qiling.")
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapped

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Salom! Men guruhdagi maxsus so'zlarni kuzatuvchi botman. "
        "Administratorlar /addword, /listwords, /delword buyruqlari orqali so'zlarni boshqarishi mumkin."
    )

# Maxsus so'z qo'shish buyrug'i
@restricted_to_admin
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Iltimos, qo'shmoqchi bo'lgan so'zni /addword dan keyin kiriting. Masalan: `/addword non`")
        return
    
    new_word = " ".join(context.args).lower().strip()
    
    if chat_id not in monitored_words:
        monitored_words[chat_id] = []
        
    if new_word in monitored_words[chat_id]:
        await update.message.reply_text(f"'{new_word}' so'zi allaqachon ro'yxatda mavjud.")
    else:
        monitored_words[chat_id].append(new_word)
        await update.message.reply_text(f"'{new_word}' so'zi muvaffaqiyatli qo'shildi.")

# Maxsus so'zlarni ko'rsatish buyrug'i
@restricted_to_admin
async def list_words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id not in monitored_words or not monitored_words[chat_id]:
        await update.message.reply_text("Kuzatiladigan maxsus so'zlar ro'yxati bo'sh.")
        return
        
    word_list = "\n".join([f"{i+1}. {word}" for i, word in enumerate(monitored_words[chat_id])])
    await update.message.reply_text(f"**Kuzatilayotgan so'zlar ro'yxati:**\n{word_list}")

# Maxsus so'zni o'chirish buyrug'i
@restricted_to_admin
async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Iltimos, o'chirmoqchi bo'lgan so'zni /delword dan keyin kiriting. Masalan: `/delword non`")
        return
    
    word_to_delete = " ".join(context.args).lower().strip()
    
    if chat_id not in monitored_words or word_to_delete not in monitored_words[chat_id]:
        await update.message.reply_text(f"'{word_to_delete}' so'zi ro'yxatda topilmadi.")
    else:
        monitored_words[chat_id].remove(word_to_delete)
        await update.message.reply_text(f"'{word_to_delete}' so'zi muvaffaqiyatli o'chirildi.")

# Guruhdagi xabarlarni kuzatish funksiyasi
async def message_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat_id = message.chat_id
    
    if message.text and chat_id in monitored_words:
        text = message.text.lower()
        
        # Maxsus so'zlarni tekshirish
        found_words = [word for word in monitored_words[chat_id] if word in text]
        
        if found_words:
            user = message.from_user
            admin_chat_id = chat_id # Xabarni guruhning o'ziga yuboramiz (yoki alohida admin ID ga o'zgartirishingiz mumkin)
            
            # Foydalanuvchi ma'lumotlari
            username = f"@{user.username}" if user.username else "mavjud emas"
            user_id = user.id
            
            # Xabarni formatlash
            report_message = (
                f"🚨 **MAXSUS SO'Z ANIQLANDI** 🚨\n\n"
                f"**Guruh:** `{message.chat.title}`\n"
                f"**Aniqalangan so'zlar:** {', '.join(found_words)}\n"
                f"**Yozgan foydalanuvchi:**\n"
                f"  - **Ism:** {user.full_name}\n"
                f"  - **Username:** {username}\n"
                f"  - **ID:** `{user_id}`\n\n"
                f"**Original xabar:**\n"
                f"> {message.text}"
            )
            
            # Adminga yuborish (guruhning o'ziga xabar berish)
            await context.bot.send_message(
                chat_id=admin_chat_id, 
                text=report_message, 
                parse_mode='Markdown'
            )
            
            # Agar siz xabarni adminlarning shaxsiy chatiga yuborishni istasangiz, avval o'sha adminlarning shaxsiy ID'larini olishingiz va ularni botga oldindan kiritishingiz kerak bo'ladi.

def main() -> None:
    # Telegram bot tokenini environment variable dan olish
    # Railwayda TOKEN deb nomlangan environment variable yaratishingiz kerak
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        raise ValueError("TOKEN environment variable topilmadi.")

    # Application yaratish
    application = Application.builder().token(TOKEN).build()

    # Buyruqlar uchun ishlovchilar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addword", add_word))
    application.add_handler(CommandHandler("listwords", list_words))
    application.add_handler(CommandHandler("delword", delete_word))
    
    # Xabarlar uchun ishlovchi (faqat guruhlardagi matnli xabarlar)
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, message_monitor))

    # Botni ishga tushirish (Webhook Railway uchun tavsiya etiladi)
    
    # Environment variable'lardan kerakli ma'lumotlarni olish
    PORT = int(os.environ.get("PORT", 8080))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # Masalan, https://<your-railway-domain>.railway.app
    
    if WEBHOOK_URL:
        # Webhook rejimi (Railway uchun)
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
        logger.info(f"Bot Webhook rejimida ishga tushdi: {WEBHOOK_URL}")
    else:
        # Polling rejimi (Agar WEBHOOK_URL berilmagan bo'lsa)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot Polling rejimida ishga tushdi.")

if __name__ == '__main__':
    main()
    
