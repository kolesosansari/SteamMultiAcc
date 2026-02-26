# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client
import logging

# Отключаем мусорные логи об устаревших пакетах
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

        client = SteamClient()
        dota = Dota2Client(client)

        @client.on('logged_on')
        def start_dota():
            print("  [~] Steam API авторизован, запускаю Dota 2 GC...")
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил, перехватываю пакеты...")
            client.sleep(1)
            
            # 1. Запрос медали
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

            # 2. Кидаем прямой запрос на Сводку порядочности (ID 7393)
            try:
                dota.send(7393, {'account_id': client.steam_id.as_32})
            except: pass

        # --- СЛУШАТЕЛИ ПАКЕТОВ ПОРЯДОЧНОСТИ ---
        
        # Перехватываем создание/обновление кэша аккаунта сервером
        @dota.on('so_create')
        @dota.on('so_update')
        def on_so_update(so):
            if hasattr(so, 'behavior_score'):
                acc_data["behavior"] = so.behavior_score
            if hasattr(so, 'communication_score'):
                acc_data["communication"] = so.communication_score

        # Перехватываем прямой ответ на наш запрос сводки (ID 7394)
        @dota.on(7394)
        def on_conduct(msg):
            if hasattr(msg, 'behavior_score'):
                acc_data["behavior"] = msg.behavior_score
            if hasattr(msg, 'communication_score'):
                acc_data["communication"] = msg.communication_score

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            # Даем скрипту 10 секунд поймать пакет с порядочностью
            while time.time() - start < 10:
                if acc_data["behavior"] > 0:
                    break
                client.sleep(0.5)
            
            acc_data["ok"] = True
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