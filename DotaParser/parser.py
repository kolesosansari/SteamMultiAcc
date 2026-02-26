# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client
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
        print(f"\n[*] Вскрытие аккаунта: {user}...")

        client = SteamClient()
        dota = Dota2Client(client)

        @client.on('logged_on')
        def start_dota():
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] GC ответил. ДЕЛАЮ ГЛУБОКИЙ ДАМП ПАРАМЕТРОВ...")
            client.sleep(2) # Ждем прогрузки кэша
            
            # --- СОЗДАНИЕ ГЛУБОКОГО ДАМПА ---
            dump_file = os.path.join(BASE_DIR, f"deep_dump_{user}.txt")
            try:
                with open(dump_file, "w", encoding="utf-8") as df:
                    df.write(f"=== DEEP DUMP FOR {user} ===\n\n")
                    if hasattr(dota, 'socache'):
                        for obj_type, obj_data in dota.socache.items():
                            df.write(f"\n[TYPE {obj_type}]\n")
                            items = []
                            if isinstance(obj_data, list): items = obj_data
                            elif isinstance(obj_data, dict): items = list(obj_data.values())
                            else: items = [obj_data]
                            
                            for obj in items:
                                df.write(f"  Class: {type(obj).__name__}\n")
                                # ВОТ ТУТ МЫ ДОСТАЕМ ВСЕ ПЕРЕМЕННЫЕ ИЗ ОБЪЕКТА
                                for attr in dir(obj):
                                    if not attr.startswith('_'): # Игнорируем системный мусор питона
                                        try:
                                            val = getattr(obj, attr)
                                            if not callable(val): # Записываем только значения (цифры, строки)
                                                df.write(f"    {attr}: {val}\n")
                                        except: pass
                    else:
                        df.write("socache пуст или отсутствует.\n")
                print(f"  [+] Файл deep_dump_{user}.txt успешно создан!")
            except Exception as e:
                print(f"  [-] Ошибка записи дампа: {e}")

            # Забираем хотя бы медаль для UI
            try:
                job_card = dota.request_profile_card(client.steam_id.as_32)
                card = dota.wait_msg(job_card, timeout=5)
                if card:
                    acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            except: pass

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while not acc_data["ok"] and time.time() - start < 15:
                client.sleep(0.5)
            
            print(f"  [v] Итог: Медаль: {acc_data['rank_name']}")
            results.append(acc_data)
            client.disconnect()
        else:
            acc_data["rank_name"] = "Ошибка входа"
            results.append(acc_data)

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[SUCCESS] Вскрытие завершено!")

if __name__ == "__main__":
    get_stats()