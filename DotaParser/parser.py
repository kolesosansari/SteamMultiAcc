# -*- coding: utf-8 -*-
import json
import os
import time
import re
from steam.client import SteamClient
from dota2.client import Dota2Client
import logging
import shutil

logging.getLogger('dota2').setLevel(logging.CRITICAL)
logging.getLogger('steam').setLevel(logging.CRITICAL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')

# Путь к папке Доты, куда она будет писать логи (ОБЯЗАТЕЛЬНО ПРОВЕРЬ ЭТОТ ПУТЬ)
# Если у тебя Дота на другом диске, поменяй этот путь!
DOTA_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota"
CONSOLE_LOG_FILE = os.path.join(DOTA_PATH, "console.log")

MEDALS = {
    0: "Без ранга",
    1: "Рекрут", 2: "Страж", 3: "Рыцарь", 4: "Герой",
    5: "Легенда", 6: "Властелин", 7: "Божество", 8: "Титан"
}

def get_medal_name(tier):
    if not tier or tier == 0: return "Без ранга"
    return f"{MEDALS.get(tier // 10, 'Unknown')} {tier % 10}"

def parse_console_log():
    """Читает файл console.log, который создала сама Дота"""
    b_score, c_score = 0, 0
    if not os.path.exists(CONSOLE_LOG_FILE):
        return b_score, c_score

    try:
        with open(CONSOLE_LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Ищем строки вида: behavior_score: 10000
            b_match = re.search(r'behavior_score(?:\s*:|:)?\s*(\d+)', content, re.IGNORECASE)
            if b_match: b_score = int(b_match.group(1))
            
            # Ищем строки вида: communication_score: 9500
            c_match = re.search(r'communication_score(?:\s*:|:)?\s*(\d+)', content, re.IGNORECASE)
            if c_match: c_score = int(c_match.group(1))
    except Exception as e:
        print(f"  [-] Ошибка чтения лога: {e}")
        
    return b_score, c_score

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
        acc_data = {"username": user, "rank_name": "Без ранга", "mmr": 0, "behavior": 0, "communication": 0, "lp": False, "ok": False}

        print(f"\n[*] Проверка аккаунта: {user}...")

        # Перед запуском удаляем старый лог-файл, чтобы не прочитать данные прошлого аккаунта
        if os.path.exists(CONSOLE_LOG_FILE):
            try: os.remove(CONSOLE_LOG_FILE)
            except: pass

        @client.on('logged_on')
        def start_dota():
            print("  [~] Steam авторизован.")
            # ЗАПУСКАЕМ ДОТУ С ПАРАМЕТРАМИ ДЛЯ СОЗДАНИЯ ЛОГА
            # -condebug заставляет игру писать всё в console.log
            # +dota_game_account_client_debug выводит инфу об аккаунте
            dota.launch(args=["-condebug", "+dota_game_account_client_debug"])

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил, ждем записи логов...")
            client.sleep(2) # Даем Доте 2 секунды, чтобы она записала файл

            # Запрашиваем медаль классическим способом
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
            except: pass

            # ЧИТАЕМ ПОРЯДОЧНОСТЬ ИЗ ФАЙЛА ЛОГОВ ДОТЫ
            b, c = parse_console_log()
            if b > 0:
                acc_data["behavior"] = b
                acc_data["communication"] = c if c > 0 else b
                print("  [+] Данные о порядочности найдены в логах игры!")
            else:
                print("  [-] Не удалось найти порядочность в console.log")

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [v] Итог: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
            results.append(acc_data)
            client.disconnect()
        else:
            acc_data["rank_name"] = "Ошибка входа"
            results.append(acc_data)

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[SUCCESS] stats.json обновлен!")

if __name__ == "__main__":
    get_stats()