# parser.py - Парсер для bezsvitla.com.ua

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

ZHMERYNKA_URL = "https://bezsvitla.com.ua/vinnytska-oblast/zmerinka"

def fetch_outage_schedule():
    """Отримує графік відключень для всіх підчерг"""
    
    try:
        print(f"🔍 Завантажую дані з {ZHMERYNKA_URL}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        today_date = datetime.now().strftime("%Y-%m-%d")
        schedules = {today_date: {}}
        
        response = requests.get(ZHMERYNKA_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            raise Exception(f"Помилка завантаження: статус {response.status_code}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Знаходимо всі блоки з чергами
        queue_blocks = soup.find_all('strong')
        
        for block in queue_blocks:
            text = block.get_text()
            match = re.search(r'Черга\s+([\d\.]+)', text)
            
            if match:
                queue_name = match.group(1)  # "1.1", "2.1", "2.2", тощо
                
                time_slots = []
                next_ul = block.find_next('ul')
                
                if next_ul:
                    items = next_ul.find_all('li')
                    
                    for item in items:
                        item_text = item.get_text(strip=True)
                        
                        # Пропускаємо час зі світлом (💡)
                        if '💡' in item_text:
                            continue
                        
                        # Витягуємо час
                        time_match = re.search(r'(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})', item_text)
                        
                        if time_match:
                            start_time = time_match.group(1)
                            end_time = time_match.group(2)
                            time_slots.append(f"{start_time}-{end_time}")
                
                schedules[today_date][queue_name] = time_slots
                print(f"✅ Черга {queue_name}: {time_slots}")
        
        # Завантажуємо графік на завтра
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_url = f"{ZHMERYNKA_URL}/grafik-na-zavtra"
        
        try:
            response_tomorrow = requests.get(tomorrow_url, headers=headers, timeout=15)
            
            if response_tomorrow.status_code == 200:
                soup_tomorrow = BeautifulSoup(response_tomorrow.text, "html.parser")
                schedules[tomorrow_date] = {}
                
                queue_blocks = soup_tomorrow.find_all('strong')
                
                for block in queue_blocks:
                    text = block.get_text()
                    match = re.search(r'Черга\s+([\d\.]+)', text)
                    
                    if match:
                        queue_name = match.group(1)
                        
                        time_slots = []
                        next_ul = block.find_next('ul')
                        
                        if next_ul:
                            items = next_ul.find_all('li')
                            
                            for item in items:
                                item_text = item.get_text(strip=True)
                                
                                if '💡' in item_text:
                                    continue
                                
                                time_match = re.search(r'(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})', item_text)
                                
                                if time_match:
                                    start_time = time_match.group(1)
                                    end_time = time_match.group(2)
                                    time_slots.append(f"{start_time}-{end_time}")
                        
                        schedules[tomorrow_date][queue_name] = time_slots
                
                print(f"✅ Завантажено графік на завтра")
        except Exception as e:
            print(f"⚠️ Не вдалося завантажити графік на завтра: {e}")
        
        print(f"✅ Графіки завантажено для {len(schedules)} дат")
        return schedules
        
    except Exception as e:
        print(f"❌ Помилка парсингу: {e}")
        import traceback
        traceback.print_exc()
        return {}

def format_schedule(time_ranges):
    """Форматує список часових проміжків"""
    if not time_ranges:
        return "✅ Відключень немає"
    
    if isinstance(time_ranges, list) and len(time_ranges) == 0:
        return "✅ Відключень немає"
    
    return "\n".join([f"⚡️ {time_range}" for time_range in time_ranges])

if __name__ == "__main__":
    print("=== ТЕСТ ПАРСЕРА ===\n")
    data = fetch_outage_schedule()
    
    if data:
        for date, queues in data.items():
            print(f"\n📅 {date}")
            for queue, times in queues.items():
                print(f"  Черга {queue}: {times}")