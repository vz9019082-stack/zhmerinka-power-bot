# bot.py - Головний файл Telegram бота з підтримкою підчерг

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from datetime import datetime, timedelta
import traceback

from config import BOT_TOKEN, QUEUES, CITY
from database import (
    init_db,
    save_user,
    get_user,
    update_user_queue,
    update_user_notify,
    get_schedule
)
from parser import fetch_outage_schedule, format_schedule
from scheduler import start_scheduler, stop_scheduler, set_bot_application, check_updates

CHOOSING_QUEUE = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        save_user(chat_id)
    
    keyboard = [
        ["📋 Графік на сьогодні", "📅 Графік на завтра"],
        ["⚙️ Обрати чергу", "🔄 Оновити графік"],
        ["ℹ️ Про бота"]
    ]
    
    welcome_text = f"""
👋 <b>Вітаю!</b>

Я бот графіків відключень електроенергії для міста <b>{CITY}</b>.

📌 <b>Що я вмію:</b>
- Показувати актуальний графік відключень
- Зберігати вашу чергу відключень
- Автоматично оновлювати дані

⚡ <b>Оберіть дію з меню нижче</b>
"""
    
    if user and user[2]:
        welcome_text += f"\n✅ Ваша черга: <b>{user[2]}</b>"
    else:
        welcome_text += "\n⚠️ Оберіть свою чергу: '⚙️ Обрати чергу'"
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )

async def show_schedule_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Графік на сьогодні"""
    await show_schedule(update, context, days_offset=0)

async def show_schedule_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Графік на завтра"""
    await show_schedule(update, context, days_offset=1)

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, days_offset=0):
    """Показує графік відключень"""
    
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user or not user[2]:
        await update.message.reply_text(
            "⚠️ Спочатку оберіть свою чергу: '⚙️ Обрати чергу'",
            parse_mode="HTML"
        )
        return
    
    user_queue = user[2]
    
    target_date = datetime.now() + timedelta(days=days_offset)
    date_str = target_date.strftime("%Y-%m-%d")
    date_readable = target_date.strftime("%d.%m.%Y")
    day_name = "сьогодні" if days_offset == 0 else "завтра"
    
    schedule = get_schedule(date_str, user_queue)
    
    if schedule is None:
        message = f"""
📅 <b>Графік на {day_name} ({date_readable})</b>
🔢 Черга: {user_queue}

⚠️ Дані ще не завантажені. Натисніть '🔄 Оновити графік'
"""
    else:
        schedule_text = format_schedule(schedule)
        message = f"""
📅 <b>Графік на {day_name} ({date_readable})</b>
🔢 Черга: {user_queue}

{schedule_text}
"""
    
    await update.message.reply_text(message, parse_mode="HTML")

async def choose_queue_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вибір черги"""
    
    # Створюємо клавіатуру з підчергами по 3 в ряд
    keyboard = []
    for i in range(0, len(QUEUES), 3):
        row = QUEUES[i:i+3]
        keyboard.append(row)
    keyboard.append(["❌ Скасувати"])
    
    await update.message.reply_text(
        "🔢 <b>Оберіть вашу чергу відключень:</b>\n\n"
        "Черга вказана у графіку від Вінницяобленерго або на сайті bezsvitla.com.ua",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )
    
    return CHOOSING_QUEUE

async def choose_queue_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Збереження обраної черги"""
    
    user_choice = update.message.text
    chat_id = update.effective_chat.id
    
    if user_choice == "❌ Скасувати":
        await return_to_main_menu(update, context)
        return ConversationHandler.END
    
    if user_choice not in QUEUES:
        await update.message.reply_text(
            "❌ Неправильний вибір. Оберіть чергу з кнопок."
        )
        return CHOOSING_QUEUE
    
    update_user_queue(chat_id, user_choice)
    
    keyboard = [
        ["📋 Графік на сьогодні", "📅 Графік на завтра"],
        ["⚙️ Обрати чергу", "🔄 Оновити графік"],
        ["ℹ️ Про бота"]
    ]
    
    await update.message.reply_text(
        f"✅ Чудово! Ваша черга: <b>{user_choice}</b>\n\n"
        f"Тепер ви можете переглядати графіки відключень.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )
    
    return ConversationHandler.END

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Про бота"""
    
    message = """
ℹ️ <b>Про бота</b>

Бот допомагає відстежувати графіки відключень електроенергії в місті Жмеринка.

<b>Джерело даних:</b>
bezsvitla.com.ua

<b>Функції:</b>
- Автоматичне оновлення графіків
- Підтримка всіх підчерг (1.1, 2.1, 2.2, тощо)
- Графік на сьогодні та завтра

<b>Команди:</b>
/start - Головне меню
/update - Оновити графік
/help - Допомога

⚠️ Графіки можуть змінюватись. Слідкуйте за офіційними джерелами!
"""
    
    await update.message.reply_text(message, parse_mode="HTML")

async def force_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оновлення графіка"""
    
    await update.message.reply_text("🔄 Оновлюю графіки, зачекайте...")
    
    try:
        check_updates()
        await update.message.reply_text(
            "✅ Графіки оновлено!\n\n"
            "Тепер ви можете переглянути актуальну інформацію.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Помилка: {str(e)}\n\nСпробуйте пізніше.",
            parse_mode="HTML"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Допомога"""
    
    message = """
📖 <b>Допомога</b>

<b>Як користуватись:</b>

1️⃣ Оберіть свою чергу ('⚙️ Обрати чергу')
2️⃣ Перегляньте графік на сьогодні або завтра
3️⃣ Оновлюйте дані за потреби

<b>Де дізнатись свою чергу?</b>
- На сайті bezsvitla.com.ua
- У графіку від Вінницяобленерго
- У додатку "Світло"

<b>Доступні черги:</b>
1.1, 2.1, 2.2, 3.1, 3.2, 4.2, 5.1, 6.1, 6.2
"""
    
    await update.message.reply_text(message, parse_mode="HTML")

async def return_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Головне меню"""
    
    keyboard = [
        ["📋 Графік на сьогодні", "📅 Графік на завтра"],
        ["⚙️ Обрати чергу", "🔄 Оновити графік"],
        ["ℹ️ Про бота"]
    ]
    
    await update.message.reply_text(
        "🏠 Головне меню",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопок"""
    
    text = update.message.text
    
    if text == "📋 Графік на сьогодні":
        await show_schedule_today(update, context)
    elif text == "📅 Графік на завтра":
        await show_schedule_tomorrow(update, context)
    elif text == "⚙️ Обрати чергу":
        await choose_queue_start(update, context)
    elif text == "ℹ️ Про бота":
        await about(update, context)
    elif text == "🔄 Оновити графік":
        await force_update(update, context)
    else:
        await update.message.reply_text(
            "❓ Використовуйте кнопки меню."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка помилок"""
    print(f"❌ Помилка: {context.error}")
    traceback.print_exc()
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😔 Сталася помилка. Спробуйте ще раз."
        )

def main():
    """Запуск бота"""
    
    print("🤖 Запуск бота...")
    
    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    set_bot_application(app)
    start_scheduler()
    
    queue_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Обрати чергу$"), choose_queue_start)],
        states={
            CHOOSING_QUEUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_queue_done)]
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Скасувати$"), return_to_main_menu)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("update", force_update))
    app.add_handler(queue_conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    
    print("✅ Бот запущено! Натисніть Ctrl+C для зупинки.")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Зупинка бота...")
        stop_scheduler()
        print("👋 Бот зупинено")
    except Exception as e:
        print(f"❌ Критична помилка: {e}")
        traceback.print_exc()
        stop_scheduler()