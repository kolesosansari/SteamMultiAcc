# -*- coding: utf-8 -*-
import json
import os
import time
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

        print(f"[*] Проверка аккаунта: {user}...")

        @client.on('logged_on')
        def start_dota():
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            try:
                # 1. Запрашиваем карточку (Ждем макс 5 секунд)
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

            try:
                # 2. Запрашиваем порядочность (Ждем макс 5 секунд)
                job_conduct = dota.request_conduct_scorecard()
                conduct = dota.wait_msg(job_conduct, timeout=5)
                if conduct:
                    acc_data["behavior"] = getattr(conduct, 'behavior_score', 0)
                    acc_data["communication"] = getattr(conduct, 'communication_score', 0)
            except Exception as e:
                pass

            # Флаг того, что мы прошли все запросы (успешно или нет - неважно)
            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            # Общий таймаут ожидания логина и запросов — 15 секунд
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [+] Успех: {acc_data['rank_name']} | Поряд: {acc_data['behavior']}")
            else:
                print("  [-] Таймаут ожидания координатора Доты.")
            
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