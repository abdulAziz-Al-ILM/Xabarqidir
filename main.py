# main.py

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))  # Admin's user ID

# Keywords storage (using a set for simplicity; persist if needed)
keywords = set()
KEYWORDS_FILE = 'keywords.txt'

# Load keywords from file if exists
if os.path.exists(KEYWORDS_FILE):
    with open(KEYWORDS_FILE, 'r') as f:
        keywords = set(line.strip().lower() for line in f if line.strip())

def save_keywords():
    with open(KEYWORDS_FILE, 'w') as f:
        for kw in sorted(keywords):
            f.write(kw + '\n')

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Bot ishga tushdi! Admin buyruqlar: /add <so\'z>, /list, /remove <so\'z>')

async def add_keyword(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text('So\'z kiriting: /add <so\'z>')
        return
    kw = ' '.join(context.args).lower()
    keywords.add(kw)
    save_keywords()
    await update.message.reply_text(f'So\'z qo\'shildi: {kw}')

async def list_keywords(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        return
    if not keywords:
        await update.message.reply_text('Maxsus so\'zlar yo\'q.')
        return
    kw_list = '\n'.join(sorted(keywords))
    await update.message.reply_text(f'Maxsus so\'zlar:\n{kw_list}')

async def remove_keyword(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text('So\'z kiriting: /remove <so\'z>')
        return
    kw = ' '.join(context.args).lower()
    if kw in keywords:
        keywords.remove(kw)
        save_keywords()
        await update.message.reply_text(f'So\'z olib tashlandi: {kw}')
    else:
        await update.message.reply_text(f'So\'z topilmadi: {kw}')

async def monitor_message(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == ADMIN_ID:
        return  # Ignore admin's messages
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Only monitor groups
    
    text = update.message.text.lower() if update.message.text else ''
    for kw in keywords:
        if kw in text:
            user = update.message.from_user
            msg = f"Keyword '{kw}' topildi!\nXabar: {update.message.text}\nFoydalanuvchi: @{user.username} (ID: {user.id})"
            await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
            break  # Send only once per message if multiple keywords

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_keyword))
    application.add_handler(CommandHandler("list", list_keywords))
    application.add_handler(CommandHandler("remove", remove_keyword))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, monitor_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
