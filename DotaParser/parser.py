# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

# Таблица медалей
MEDALS = {
    0: "Без ранга",
    1: "Рекрут", 2: "Страж", 3: "Рыцарь", 4: "Герой",
    5: "Легенда", 6: "Властелин", 7: "Божество", 8: "Титан"
}

def get_medal_name(tier):
    if not tier or tier == 0: return "Unranked"
    major = tier // 10
    minor = tier % 10
    return f"{MEDALS.get(major, 'Unknown')} {minor}"

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH): return
    
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
            "rank_name": "Unknown", 
            "mmr": 0, 
            "behavior": 10000, # По умолчанию
            "avatar": "", 
            "lp": False, 
            "ok": False
        }

        @client.on('logged_on')
        def start_dota():
            # Исправленный способ получения аватарки
            acc_data["avatar"] = client.user.get_avatar_url()
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            dota.request_profile_card(client.steam_id.as_32)

        @dota.on('profile_card')
        def parse_card(account_id, card):
            acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            # В карточке rank_tier 31 это и есть "3 звезда 1 медаль"
            acc_data["mmr"] = getattr(card, 'rank_tier', 0) 
            acc_data["behavior"] = getattr(card, 'behavior_score', 10000)
            
            if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                acc_data["lp"] = True
            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 20:
                client.sleep(0.1)
            results.append(acc_data)
            client.disconnect()
        else:
            results.append({"username": user, "rank_name": "Ошибка входа", "mmr": -1})

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    get_stats()