# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

# Словарь для перевода рангов
MEDALS = {
    0: "Unranked",
    1: "Herald", 2: "Guardian", 3: "Crusader", 4: "Archon",
    5: "Legend", 6: "Ancient", 7: "Divine", 8: "Immortal"
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
            "behavior": 0, 
            "avatar": "", 
            "lp": False, 
            "ok": False
        }

        @client.on('logged_on')
        def start_dota():
            # Получаем аватарку через Steam
            persona = client.get_persona(client.steam_id)
            acc_data["avatar"] = str(persona.avatar_url) if persona else ""
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            dota.request_profile_card(client.steam_id.as_32)

        @dota.on('profile_card')
        def parse_card(account_id, card):
            acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            # ПТС часто лежит в поле leaderboard_rank или требует доп. запроса
            # Но в карточке можно достать только примерный тир
            acc_data["mmr"] = getattr(card, 'rank_tier', 0) # Для примера пока оставим тир
            
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
            results.append({"username": user, "rank_name": "Login Error", "mmr": -1})

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    get_stats()