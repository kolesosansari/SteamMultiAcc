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
            "behavior": 0, 
            "communication": 0,
            "lp": False, 
            "ok": False
        }

        @dota.on('ready')
        def fetch_data():
            # Запрашиваем карточку (ранг и ПТС в слотах)
            dota.request_profile_card(client.steam_id.as_32)
            # Запрашиваем сводку порядочности и вежливости
            dota.request_conduct_scorecard()

        @dota.on('profile_card')
        def parse_card(account_id, card):
            acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            # Ищем ПТС в слотах, если они выставлены на показ
            for slot in getattr(card, 'slots', []):
                if hasattr(slot, 'stat') and slot.stat.stat_id == 1: # 1 обычно Solo MMR
                    acc_data["mmr"] = slot.stat.stat_score
            
            if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                acc_data["lp"] = True

        @dota.on('conduct_scorecard')
        def parse_conduct(msg):
            # behavior_score и communication_score — те самые цифры до 12000
            acc_data["behavior"] = getattr(msg, 'behavior_score', 0)
            acc_data["communication"] = getattr(msg, 'communication_score', 0)
            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 25:
                client.sleep(0.5)
            results.append(acc_data)
            client.disconnect()
        else:
            results.append({"username": user, "rank_name": "Ошибка входа"})

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    get_stats()