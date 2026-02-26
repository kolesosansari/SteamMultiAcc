# -*- coding: utf-8 -*-
import json
import os
import time
from steam.client import SteamClient
from dota2.client import Dota2Client
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, '../accounts.txt')
STATS_PATH = os.path.join(BASE_DIR, '../stats.json')
DEBUG_LOG_PATH = os.path.join(BASE_DIR, 'dota_gc_debug.log')

# === ВКЛЮЧАЕМ РЕЖИМ ПРОСЛУШКИ ===
# Записываем все сырые пакеты от сервера в лог
logging.basicConfig(
    filename=DEBUG_LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
# Отключаем вывод дебага прямо в консоль, чтобы не засорять экран
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

MEDALS = {
    0: "Без ранга", 1: "Рекрут", 2: "Страж", 3: "Рыцарь", 4: "Герой",
    5: "Легенда", 6: "Властелин", 7: "Божество", 8: "Титан"
}

def get_medal_name(tier):
    if not tier or tier == 0: return "Без ранга"
    return f"{MEDALS.get(tier // 10, 'Unknown')} {tier % 10}"

def get_stats():
    if not os.path.exists(ACCOUNTS_PATH): return
        
    # Чистим лог перед стартом
    if os.path.exists(DEBUG_LOG_PATH):
        open(DEBUG_LOG_PATH, 'w').close()

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
            print("  [~] Координатор Доты ответил, ДАМПИМ КЭШ СЕРВЕРА...")
            client.sleep(2)
            
            # --- ДЕБАГ: СОХРАНЯЕМ ВЕСЬ ВНУТРЕННИЙ КЭШ В ТЕКСТОВИК ---
            try:
                dump_file_path = os.path.join(BASE_DIR, f"socache_dump_{user}.txt")
                with open(dump_file_path, "w", encoding="utf-8") as dump_file:
                    dump_file.write(f"--- DUMP SOCACHE FOR {user} ---\n")
                    if hasattr(dota, 'socache'):
                        for obj_type in dota.socache:
                            dump_file.write(f"\n==== TYPE: {obj_type} ====\n")
                            for obj in dota.socache[obj_type]:
                                dump_file.write(str(obj) + "\n")
                    else:
                        dump_file.write("SOCACHE MISSING!\n")
                print(f"  [+] Дамп кэша сохранен в файл: socache_dump_{user}.txt")
            except Exception as e:
                print(f"  [-] Ошибка создания дампа: {e}")

            # 1. Запрос медали
            try:
                job_card = dota.request_profile_card(client.steam_id.as_32)
                card = dota.wait_msg(job_card, timeout=5)
                if card:
                    acc_data["rank_name"] = get_medal_name(getattr(card, 'rank_tier', 0))
            except: pass

            # 2. Прямой запрос порядочности (на всякий случай)
            try:
                dota.send(7393, {'account_id': client.steam_id.as_32})
            except: pass

        # Слушатели для сбора, если пакет всё-таки придет
        @dota.on('so_create')
        @dota.on('so_update')
        def on_so_update(so):
            if hasattr(so, 'behavior_score'): acc_data["behavior"] = so.behavior_score
            if hasattr(so, 'communication_score'): acc_data["communication"] = so.communication_score

        @dota.on(7394)
        def on_conduct(msg):
            if hasattr(msg, 'behavior_score'): acc_data["behavior"] = msg.behavior_score
            if hasattr(msg, 'communication_score'): acc_data["communication"] = msg.communication_score

        result = client.login(user, password)
        if result == 1:
            start = time.time()
            while time.time() - start < 10:
                if acc_data["behavior"] > 0: break
                client.sleep(0.5)
            
            acc_data["ok"] = True
            print(f"  [v] Итог: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
            results.append(acc_data)
            client.disconnect()
        else:
            acc_data["rank_name"] = "Ошибка входа"
            results.append(acc_data)

    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("\n[!!!] ГОТОВО! ПРОВЕРЬ НОВЫЕ ФАЙЛЫ В ПАПКЕ DotaParser!")

if __name__ == "__main__":
    get_stats()