# -*- coding: utf-8 -*-
import json
import os
import time
import re
from steam.client import SteamClient
from dota2.client import Dota2Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

MEDALS = {
    0: "Без ранга",
    1: "Рекрут", 2: "Страж", 3: "Рыцарь", 4: "Герой",
    5: "Легенда", 6: "Властелин", 7: "Божество", 8: "Титан"
}

def get_medal_name(tier):
    if not tier or tier == 0: return "Без ранга"
    major = tier // 10
    minor = tier % 10
    return f"{MEDALS.get(major, 'Unknown')} {minor}"

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH): 
        print("accounts.txt не найден!")
        return
        
    results = []
    with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2: continue
        user, password = parts[0], parts[1]
        
        client = SteamClient()
        dota = Dota2Client(client)
        acc_data = {
            "username": user, 
            "rank_name": "Без ранга", 
            "mmr": 0, 
            "behavior": 0, 
            "communication": 0,
            "lp": False, 
            "ok": False
        }

        print(f"\n[*] Проверка аккаунта: {user}...")

        @client.on('logged_on')
        def start_dota():
            print("  [~] Успешный логин, получаю скрытую страницу GDPR...")
            try:
                session = client.get_web_session()
                if session:
                    # Используем точный 64-битный ID для надежности
                    url = f"https://steamcommunity.com/profiles/{client.steam_id}/gcpd/570/?category=Account&tab=MatchPlayerReportIncoming"
                    res = session.get(url, timeout=15)
                    
                    # СОХРАНЯЕМ СТРАНИЦУ ДЛЯ ДЕБАГА
                    debug_file = os.path.join(BASE_DIR, f"debug_{user}.html")
                    with open(debug_file, "w", encoding="utf-8") as df:
                        df.write(res.text)
                        
                    # ИЩЕМ ДАННЫЕ УМНЫМ СПОСОБОМ
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', res.text, re.DOTALL | re.IGNORECASE)
                    found_scores = False
                    
                    for row in reversed(rows): # Идем с конца (самые свежие данные)
                        # Ищем все ячейки только с числами
                        cols = re.findall(r'<td[^>]*>\s*(\d+)\s*</td>', row, re.IGNORECASE)
                        if len(cols) >= 2:
                            b_score = int(cols[-2])
                            c_score = int(cols[-1])
                            # Базовая проверка на адекватность
                            if 0 < b_score <= 12000 and 0 < c_score <= 12000:
                                acc_data["behavior"] = b_score
                                acc_data["communication"] = c_score
                                found_scores = True
                                print(f"  [+] Найдена Порядочность: {b_score}, Вежливость: {c_score}")
                                break
                                
                    if not found_scores:
                        print(f"  [-] Цифры не найдены! Открой файл {debug_file} и посмотри, что ответил Steam.")
                else:
                    print("  [-] Не удалось получить web-сессию Steam.")
            except Exception as e:
                print(f"  [-] Ошибка при парсинге GDPR: {e}")
            
            print("  [~] Запускаю Dota 2 для получения медали...")
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            try:
                job_card = dota.request_profile_card(client.steam_id.as_32)
                card = dota.wait_msg(job_card, timeout=5)
                if card:
                    acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
                    for slot in getattr(card, 'slots', []):
                        if hasattr(slot, 'stat') and slot.stat.stat_id == 1:
                            acc_data["mmr"] = slot.stat.stat_score
                    if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                        acc_data["lp"] = True
            except Exception as e:
                pass

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [v] Данные собраны!")
            else:
                print("  [-] Таймаут ожидания GC Dota 2.")
            
            results.append(acc_data)
            client.disconnect()
        else:
            acc_data["rank_name"] = "Ошибка входа"
            results.append(acc_data)
            print("  [-] Ошибка логина Steam.")

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[SUCCESS] stats.json обновлен!")

if __name__ == "__main__":
    get_stats()