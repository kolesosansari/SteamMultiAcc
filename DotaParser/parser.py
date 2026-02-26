# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

results = []

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH):
        print("[-] accounts.txt not found!")
        return

    try:
        with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        with open(ACCOUNTS_PATH, 'r', encoding='cp1251') as f:
            lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2: continue
        
        user, password = parts[0], parts[1]
        print(f"[*] Checking: {user}...")

        client = SteamClient()
        dota = Dota2Client(client)
        acc_data = {"username": user, "rank": 0, "lp": False, "ok": False}

        @client.on('logged_on')
        def start_dota():
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            dota.request_profile_card(client.steam_id.as_32)

        @dota.on('profile_card')
        def parse_card(account_id, card):
            acc_data["rank"] = getattr(card, 'rank_tier', 0)
            if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                acc_data["lp"] = True
            acc_data["ok"] = True
            print(f"  [+] Done: Rank {acc_data['rank']}")

        result = client.login(user, password)
        if result != 1:
            results.append({"username": user, "rank": -1, "lp": False})
            continue

        start = time.time()
        while not acc_data["ok"] and time.time() - start < 20:
            client.sleep(0.1)
        
        results.append(acc_data)
        client.disconnect()

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[SUCCESS] stats.json created!")

if __name__ == "__main__":
    get_stats()