# -*- coding: utf-8 -*-
import json
import os
import time
import re
from steam.client import SteamClient
from dota2.client import Dota2Client
import logging

# Убираем спам "Unsupported type" от библиотеки dota2
logging.getLogger('dota2').setLevel(logging.ERROR)

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
            dota.launch()

        @dota.on('ready')
        def fetch_data():
            print("  [~] Координатор Доты ответил, читаю медаль...")
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
                print("  [-] Не удалось получить карточку профиля Доты")

            acc_data["ok"] = True

        result = client.login(user, password)
        if result == 1:
            print("  [~] Steam авторизован, получаю скрытую страницу GDPR...")
            try:
                session = client.get_web_session()
                if session is None:
                    print("  [!] ОШИБКА: get_web_session() вернул None!")
                    print("  [!] Библиотека steam сломана. Выполни команду обновления через pip (в ответе выше)!")
                else:
                    url = f"https://steamcommunity.com/profiles/{client.steam_id}/gcpd/570/?category=Account&tab=MatchPlayerReportIncoming"
                    res = session.get(url, timeout=10)
                    if "MatchPlayerReportIncoming" not in res.url:
                        print("  [-] Ошибка WebAPI: Steam не пустил на страницу (Редирект).")
                    else:
                        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', res.text, re.DOTALL | re.IGNORECASE)
                        found = False
                        for row in reversed(rows):
                            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                            nums = []
                            for td in tds:
                                text = re.sub(r'<[^>]+>', '', td).strip()
                                text = re.sub(r'[\s,.]+', '', text) # Убираем пробелы и запятые из цифр 10 000
                                if text.isdigit():
                                    nums.append(int(text))
                            
                            if len(nums) >= 2:
                                b, c = nums[-2], nums[-1]
                                if 1 <= b <= 12000 and 1 <= c <= 12000:
                                    acc_data["behavior"] = b
                                    acc_data["communication"] = c
                                    found = True
                                    print(f"  [+] GDPR успешно: Порядочность {b}, Вежливость {c}")
                                    break
                        if not found:
                            print("  [-] Данные в таблице GDPR не найдены (аккаунт новый или нет репортов).")
            except Exception as e:
                print(f"  [-] Ошибка при парсинге GDPR: {e}")

            start = time.time()
            # Ждем завершения работы Доты
            while not acc_data["ok"] and time.time() - start < 10:
                client.sleep(0.5)
            
            if acc_data["ok"]:
                print(f"  [v] Итог: Медаль: {acc_data['rank_name']} | Поряд: {acc_data['behavior']} | Вежл: {acc_data['communication']}")
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