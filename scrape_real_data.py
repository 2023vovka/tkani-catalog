import asyncio
import sqlite3
import csv
import os
import re
from playwright.async_api import async_playwright

def extract_characteristics(text):
    # Убираем пробелы и запятые в тысячах (например, "100 000" -> "100000")
    clean_text = re.sub(r'(\d)[\s.,](\d{3})', r'\1\2', text)
    
    density, martindale = None, None
    
    # Поиск плотности (учитывает английский, литовский, польский)
    match_density = re.search(r'(?i)(?:weight|svoris|gramatura|grammage)[^\d]{0,50}?(\d{2,4})\s*(?:g/m|g)', clean_text)
    if match_density:
        density = int(match_density.group(1))
        
    # Поиск Мартиндейла
    match_martindale = re.search(r'(?i)(?:martindale|trinčiai|abrasion|rub|ścieralność)[^\d]{0,50}?(\d{4,6})', clean_text)
    if match_martindale:
        martindale = int(match_martindale.group(1))
        
    return density, martindale

async def main():
    db_path = 'fabrics.db'
    if not os.path.exists(db_path):
        print("База данных не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Выбираем все ткани, у которых есть ссылка
    cursor.execute("SELECT id, name, manufacturer, product_url, density, martindale FROM fabrics WHERE product_url IS NOT NULL AND product_url != ''")
    rows = cursor.fetchall()
    
    print(f"Всего тканей со ссылками для сканирования: {len(rows)}")
    print("Внимание: процесс может занять некоторое время, так как скрипт будет по-настоящему открывать каждую ссылку.")

    updated_count = 0

    async with async_playwright() as p:
        # Запускаем скрытый браузер
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        for idx, row in enumerate(rows):
            fid, name, manufacturer, url, old_density, old_martindale = row
            print(f"\n[{idx+1}/{len(rows)}] Сканируем {name} ({manufacturer}) - {url}")
            
            try:
                # Открываем страницу (с таймаутом 15 секунд, чтобы не зависать)
                response = await page.goto(url, timeout=15000)
                if response is None or response.status >= 400:
                    print(" -> Ошибка: страница недоступна (404/403)")
                    continue
                    
                await asyncio.sleep(1.5) # Даем прогрузиться JS
                
                # Извлекаем весь текст со страницы
                text = await page.locator("body").inner_text()
                
                new_density, new_martindale = extract_characteristics(text)
                
                # Если скрипт нашел реальные цифры на сайте, используем их. Иначе оставляем старые
                d = new_density if new_density else old_density
                m = new_martindale if new_martindale else old_martindale
                
                # Если найденные данные отличаются от тех, что в базе
                if d != old_density or m != old_martindale:
                    cursor.execute("UPDATE fabrics SET density = ?, martindale = ? WHERE id = ?", (d, m, fid))
                    conn.commit()
                    updated_count += 1
                    print(f" -> НАЙДЕНЫ РЕАЛЬНЫЕ ДАННЫЕ! Плотность: {d or 'нет'}, Мартиндейл: {m or 'нет'}")
                else:
                    if new_density or new_martindale:
                        print(" -> Данные на сайте совпадают с базой.")
                    else:
                        print(" -> Характеристики на странице не найдены. Оставляем текущие значения.")
                    
            except Exception as e:
                print(f" -> Ошибка загрузки (таймаут или блок): {e}")

        await browser.close()
        
    print(f"\nСкрапинг завершен. Обновлено тканей точными данными с сайтов производителей: {updated_count}")

    # Перезапись CSV
    dir_name = "данные о тканях для notebooklm"
    os.makedirs(dir_name, exist_ok=True)
    cursor.execute("""
    SELECT 
        name AS 'Название', manufacturer AS 'Производитель', category AS 'Категория', 
        price AS 'Розничная цена', wholesale_price AS 'Оптовая цена', 
        density AS 'Плотность (г/м2)', martindale AS 'Мартиндейл (циклы)', 
        properties AS 'Свойства', fabric_type AS 'Тип ткани', product_url AS 'Ссылка на товар' 
    FROM fabrics
    """)
    export_rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()

    csv_path = os.path.join(dir_name, "fabrics_data.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(columns)
        writer.writerows(export_rows)
        
    print(f"Таблица обновлена актуальными данными: {csv_path}")

if __name__ == "__main__":
    asyncio.run(main())
