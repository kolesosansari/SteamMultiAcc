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
            print("  [~] Steam авторизован, запускаю Dota 2 GC...")
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил!")
            client.sleep(1) # Даем координатору прогрузиться

            # 1. ЗАПРАШИВАЕМ МЕДАЛЬ (таймаут 5 секунд)
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
            except Exception:
                pass

            # 2. ЗАПРАШИВАЕМ ПОРЯДОЧНОСТЬ У КООРДИНАТОРА (таймаут 5 секунд)
            try:
                job_conduct = dota.request_conduct_scorecard()
                conduct = dota.wait_msg(job_conduct, timeout=5)
                if conduct:
                    acc_data["behavior"] = getattr(conduct, 'behavior_score', 0)
                    acc_data["communication"] = getattr(conduct, 'communication_score', 0)
            except Exception:
                pass

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            # 3. ПОКА ДОТА ГРУЗИТСЯ, ПЫТАЕМСЯ ВЫТЯНУТЬ ЦИФРЫ ИЗ STEAM WEB API (Страница GDPR)
            client.sleep(2) # Пауза для получения веб-токенов
            session = client.get_web_session()
            if session:
                try:
                    url = f"https://steamcommunity.com/profiles/{client.steam_id}/gcpd/570/?category=Account&tab=MatchPlayerReportIncoming"
                    res = session.get(url, timeout=8)
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', res.text, re.DOTALL | re.IGNORECASE)
                    for row in reversed(rows):
                        cols = re.findall(r'<td[^>]*>\s*(\d+)\s*</td>', row, re.IGNORECASE)
                        if len(cols) >= 2:
                            b = int(cols[-2])
                            c = int(cols[-1])
                            if b > 0 and c > 0:
                                acc_data["behavior"] = b
                                acc_data["communication"] = c
                                break
                except Exception:
                    pass

            start = time.time()
            # Ждем завершения работы Доты (не больше 15 секунд)
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [v] Данные собраны! Медаль: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
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