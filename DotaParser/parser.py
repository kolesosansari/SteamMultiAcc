# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client

# ?????????? ???? ???????????? ????? ???????
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

results = []

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH):
        print("[-] Error: accounts.txt not found!")
        return

    try:
        with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # ???? ????? accounts.txt ? ?????? ???????? ?????????
        with open(ACCOUNTS_PATH, 'r', encoding='cp1251') as f:
            lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2: continue
        
        user, password = parts[0], parts[1]
        print(f"[*] Checking: {user}...")

        client = SteamClient()
        dota = Dota2Client(client)

        @client.on('logged_on')
        def start_dota():
            print(f"  [+] Steam Logged. Starting Dota...")
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print(f"  [+] Dota Ready. Requesting card...")
            dota.request_profile_card(client.steam_id.as_32)

        @dota.on('profile_card')
        def parse_card(account_id, card):
            rank = getattr(card, 'rank_tier', 0)
            is_lp = False
            if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                is_lp = True

            print(f"  [!] Rank: {rank}, LP: {is_lp}")
            results.append({"username": user, "rank": rank, "lp": is_lp})
            dota.exit()
            client.disconnect()

        result = client.login(user, password)
        if result != 1:
            print(f"  [-] Login failed for {user}. Code: {result}")
            results.append({"username": user, "rank": "ERROR", "lp": False})
            continue

        client.run_away(timeout=20)

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[DONE] stats.json updated!")

if __name__ == "__main__":
    get_stats()