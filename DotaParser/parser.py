# -*- coding: utf-8 -*-
import json
import os
import time
import re
from steam.client import SteamClient
from dota2.client import Dota2Client
import logging

# Вырубаем спам об ошибках от библиотек
logging.getLogger('dota2').setLevel(logging.ERROR)
logging.getLogger('steam').setLevel(logging.ERROR)

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
            "ok": False,
            "card_ok": False,
            "conduct_ok": False
        }

        print(f"\n[*] Проверка аккаунта: {user}...")

        @client.on('logged_on')
        def start_dota():
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил, перехватываю пакеты...")
            client.sleep(1.5)

            # Способ 1: Читаем внутренний кеш Доты (самый надежный способ без запросов)
            if hasattr(dota, 'socache'):
                try:
                    for obj_type in dota.socache:
                        for obj in dota.socache[obj_type]:
                            if hasattr(obj, 'behavior_score'):
                                acc_data["behavior"] = obj.behavior_score
                                acc_data["communication"] = getattr(obj, 'communication_score', obj.behavior_score)
                                acc_data["conduct_ok"] = True
                                print(f"  [+] Найдено в кеше игры: Порядочность {acc_data['behavior']}")
                except: pass

            # Способ 2: Параллельно кидаем асинхронные запросы
            dota.request_profile_card(client.steam_id.as_32)
            try: dota.request_conduct_scorecard()
            except: pass
            try: dota.send(7393, {'account_id': client.steam_id.as_32}) # Прямой пакет
            except: pass

        # --- СЛУШАТЕЛИ ОТВЕТОВ (Сработают мгновенно, как только сервер ответит) ---
        @dota.on('profile_card')
        def parse_card(account_id, card):
            acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            for slot in getattr(card, 'slots', []):
                if hasattr(slot, 'stat') and slot.stat.stat_id == 1:
                    acc_data["mmr"] = slot.stat.stat_score
            if hasattr(card, 'low_priority_until_date') and card.low_priority_until_date > time.time():
                acc_data["lp"] = True
            acc_data["card_ok"] = True
            print(f"  [+] Медаль профиля: {acc_data['rank_name']}")

        @dota.on('PlayerConductScorecard')
        def parse_conduct(msg):
            if not acc_data["conduct_ok"]:
                acc_data["behavior"] = getattr(msg, 'behavior_score', 0)
                acc_data["communication"] = getattr(msg, 'communication_score', getattr(msg, 'behavior_score', 0))
                acc_data["conduct_ok"] = True
                print(f"  [+] Сводка получена: Порядочность {acc_data['behavior']}")

        @dota.on(7394)
        def parse_conduct_raw(msg):
            if not acc_data["conduct_ok"]:
                acc_data["behavior"] = getattr(msg, 'behavior_score', 0)
                acc_data["communication"] = getattr(msg, 'communication_score', getattr(msg, 'behavior_score', 0))
                acc_data["conduct_ok"] = True
                print(f"  [+] Сводка (RAW) получена: Порядочность {acc_data['behavior']}")

        # --- ОСНОВНАЯ ЛОГИКА ---
        result = client.login(user, password)
        if result == 1:
            # Способ 3: Тихий WebAPI (Без вывода ошибок, если Стим нас блочит)
            try:
                session = client.get_web_session()
                if session:
                    url = f"https://steamcommunity.com/profiles/{client.steam_id}/gcpd/570/?category=Account&tab=MatchPlayerReportIncoming"
                    res = session.get(url, timeout=5)
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
                                acc_data["behavior"], acc_data["communication"] = b, c
                                acc_data["conduct_ok"] = True
                                print(f"  [+] Скрытая таблица Steam: Порядочность {b}")
                                break
            except: pass

            # Ждем максимум 10 секунд, пока отработают слушатели
            start = time.time()
            while time.time() - start < 10:
                if acc_data["card_ok"] and acc_data["conduct_ok"]:
                    break
                client.sleep(0.5)
            
            acc_data["ok"] = True
            print(f"  [v] Итог: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
            
            # Чистим временные ключи
            for k in ["card_ok", "conduct_ok"]:
                acc_data.pop(k, None)
                
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