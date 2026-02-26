# -*- coding: utf-8 -*-
import json
import os
import time
import re
from steam.client import SteamClient
from dota2.client import Dota2Client
from steam.webauth import WebAuth # Используем прямую браузерную авторизацию
import logging

logging.getLogger('dota2').setLevel(logging.CRITICAL)
logging.getLogger('steam').setLevel(logging.CRITICAL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

MEDALS = {
    0: "Без ранга", 1: "Рекрут", 2: "Страж", 3: "Рыцарь", 4: "Герой",
    5: "Легенда", 6: "Властелин", 7: "Божество", 8: "Титан"
}

def get_medal_name(tier):
    if not tier or tier == 0: return "Без ранга"
    return f"{MEDALS.get(tier // 10, 'Unknown')} {tier % 10}"

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH): return
        
    results = []
    with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2: continue
        user, password = parts[0], parts[1]
        
        acc_data = {"username": user, "rank_name": "Без ранга", "mmr": 0, "behavior": 0, "communication": 0, "lp": False, "ok": False}
        print(f"\n[*] Проверка аккаунта: {user}...")

        # 1. ПРЯМАЯ БРАУЗЕРНАЯ АВТОРИЗАЦИЯ ДЛЯ ПОРЯДОЧНОСТИ
        try:
            print("  [~] Вхожу через WebAuth (эмуляция браузера)...")
            wa = WebAuth(user)
            session = wa.login(password)
            
            if session:
                url = f"https://steamcommunity.com/profiles/{wa.steam_id}/gcpd/570/?category=Account&tab=MatchPlayerReportIncoming"
                res = session.get(url, timeout=10)
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', res.text, re.DOTALL | re.IGNORECASE)
                for row in reversed(rows):
                    cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    nums = []
                    for td in cols:
                        text = re.sub(r'<[^>]+>', '', td).strip()
                        text = re.sub(r'[\s,.]+', '', text)
                        if text.isdigit(): nums.append(int(text))
                    if len(nums) >= 2:
                        b, c = nums[-2], nums[-1]
                        if 1 <= b <= 12000 and 1 <= c <= 12000:
                            acc_data["behavior"] = b
                            acc_data["communication"] = c
                            print(f"  [+] WebAPI: Порядочность {b}, Вежливость {c}")
                            break
            else:
                print("  [-] WebAuth вернул пустую сессию.")
        except Exception as e:
            print(f"  [-] Ошибка WebAuth: {e}")

        # 2. АВТОРИЗАЦИЯ В КЛИЕНТЕ РАДИ МЕДАЛИ
        client = SteamClient()
        dota = Dota2Client(client)

        @client.on('logged_on')
        def start_dota():
            print("  [~] Steam API авторизован, получаю медаль профиля...")
            dota.launch() # Без параметров, просто логин в координатор

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
                    print(f"  [+] Медаль получена: {acc_data['rank_name']}")
            except: pass
            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            print(f"  [v] Итог: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
            results.append(acc_data)
            client.disconnect()
        else:
            acc_data["rank_name"] = "Ошибка входа"
            results.append(acc_data)
            print("  [-] Ошибка логина Steam Client.")

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[SUCCESS] stats.json обновлен!")

if __name__ == "__main__":
    get_stats()