from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TOKEN
from database import create_tables
from handlers import (
    start,
    handle_message,
    handle_paid_button,
    handle_delete_button,
)
from reminders import post_init


create_tables()

app = Application.builder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_paid_button, pattern="^paid:"))
app.add_handler(CallbackQueryHandler(handle_delete_button, pattern="^delete_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ Бот запущен...")

app.run_polling()