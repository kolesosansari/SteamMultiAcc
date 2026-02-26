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

        print(f"\n[*] Проверка аккаунта: {user}...")

        @client.on('logged_on')
        def start_dota():
            print("  [~] Успешный логин Steam, запускаю Dota 2 GC...")
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил!")
            # Даем клиенту 1.5 секунды, чтобы он успел обработать пакет account_info, который присылается при старте
            client.sleep(1.5)

            # 1. ЧИТАЕМ ПОРЯДОЧНОСТЬ ИЗ БАЗОВОЙ ИНФЫ (Без запросов!)
            if dota.account_info:
                acc_data["behavior"] = getattr(dota.account_info, 'behavior_score', 0)
                acc_data["communication"] = getattr(dota.account_info, 'communication_score', 0)
                print(f"  [+] Порядочность: {acc_data['behavior']} | Вежливость: {acc_data['communication']}")
            else:
                print("  [-] Координатор не прислал account_info.")

            # 2. Быстрый запрос карточки для получения медали
            print("  [~] Читаю медаль профиля...")
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
                print("  [-] Ошибка при парсинге медали.")

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            # Ждем макс 15 секунд на всю процедуру
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [v] Данные собраны! Медаль: {acc_data['rank_name']}")
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