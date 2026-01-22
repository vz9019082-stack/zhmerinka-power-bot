# scheduler.py - Автоматична перевірка оновлень

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from parser import fetch_outage_schedule
from database import save_schedule, get_schedule, get_all_users_by_queue
from config import CHECK_INTERVAL_MINUTES

scheduler = BackgroundScheduler(timezone="Europe/Kyiv")
bot_application = None

def set_bot_application(app):
    """Встановлює посилання на бота"""
    global bot_application
    bot_application = app

async def send_notification(chat_id, message):
    """Відправляє сповіщення"""
    try:
        if bot_application:
            await bot_application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML"
            )
            print(f"✅ Надіслано сповіщення {chat_id}")
    except Exception as e:
        print(f"❌ Помилка відправки {chat_id}: {e}")

def check_updates():
    """Перевірка оновлень"""
    try:
        print(f"\n🔄 Перевірка: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        new_data = fetch_outage_schedule()
        
        if not new_data:
            print("⚠️ Не вдалося отримати дані")
            return
        
        changes_found = False
        
        for date, queues_data in new_data.items():
            for queue, time_ranges in queues_data.items():
                
                old_schedule = get_schedule(date, queue)
                
                if old_schedule != time_ranges:
                    changes_found = True
                    print(f"📢 Зміна: {date}, Черга {queue}")
                    print(f"   Старий: {old_schedule}")
                    print(f"   Новий: {time_ranges}")
                    
                    save_schedule(date, queue, time_ranges)
                    
                    if bot_application and old_schedule is not None:
                        message = f"""
🔔 <b>ЗМІНА ГРАФІКУ!</b>

📅 Дата: {date}
🔢 Черга: {queue}

<b>Новий графік:</b>
{format_time_ranges(time_ranges)}
"""
                        users = get_all_users_by_queue(queue)
                        print(f"   Сповіщення {len(users)} користувачам...")
                        
                        import asyncio
                        for user_id in users:
                            asyncio.create_task(send_notification(user_id, message))
                else:
                    save_schedule(date, queue, time_ranges)
        
        if not changes_found:
            print("✅ Змін немає")
        else:
            print("✅ Оновлення завершено")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()

def format_time_ranges(time_ranges):
    """Форматує часові проміжки"""
    if not time_ranges:
        return "✅ Відключень немає"
    
    if isinstance(time_ranges, list) and len(time_ranges) == 0:
        return "✅ Відключень немає"
    
    return "\n".join([f"⚡️ {tr}" for tr in time_ranges])

def start_scheduler():
    """Запуск планувальника"""
    print(f"⏰ Планувальник (кожні {CHECK_INTERVAL_MINUTES} хв)")
    
    scheduler.add_job(
        check_updates,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="check_outages",
        replace_existing=True,
        next_run_time=datetime.now()
    )
    
    scheduler.start()
    print("✅ Планувальник запущено")

def stop_scheduler():
    """Зупинка планувальника"""
    try:
        scheduler.shutdown()
        print("⏹️ Планувальник зупинено")
    except:
        pass
