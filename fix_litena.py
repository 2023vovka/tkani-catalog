import asyncio
import sqlite3
import re
import os
from playwright.async_api import async_playwright

def clean_number(text):
    if not text:
        return None
    digits = re.sub(r'[^\d]', '', text)
    if digits:
        return int(digits)
    return None

def extract_litena_data(text, html=""):
    # Очищаем текст
    clean_text = re.sub(r'\s+', ' ', text)
    clean_html = re.sub(r'\s+', ' ', html)
    
    # 1. МАРТИНДЕЙЛ
    martindale = None
    # Вариант 1: Ключевое слово перед числом
    match_martindale = re.search(r'(?i)(?:martindale|trinties|trinčiai|atsparumas|ciklų)[^\d]{0,50}?([><~]?\s*\d{2,3}[\s.,]*\d{3})', clean_text)
    if not match_martindale:
        # Вариант 2: Число перед ключевым словом (как на сайте Litena: 100.000 Martindale testas)
        match_martindale = re.search(r'(?i)([><~]?\s*\d{2,3}[\s.,]*\d{3})[a-z\s.,-]{0,50}?(?:martindale|trinties|trinčiai|atsparumas|testas|ciklų)', clean_text)
        
    if match_martindale:
        martindale = clean_number(match_martindale.group(1))

    # 2. ТИП ТКАНИ (Словарь Литовский -> Русский)
    fabric_type = None
    text_lower = clean_text.lower()
    
    if "dirbtinė oda" in text_lower or "eko oda" in text_lower or "eko-oda" in text_lower or "dirbtine oda" in text_lower:
        fabric_type = "Экокожа"
    elif "veliūras" in text_lower or "velvetas" in text_lower or "veliuras" in text_lower:
        fabric_type = "Велюр"
    elif "šenilas" in text_lower or "šenilinis" in text_lower or "senilas" in text_lower:
        fabric_type = "Шенилл"
    elif "žakardas" in text_lower or "zakardas" in text_lower:
        fabric_type = "Жаккард"
    elif "pintas audinys" in text_lower or "stambaus pynimo" in text_lower or "austas audinys" in text_lower:
        fabric_type = "Рогожка"
    elif "mikropluoštas" in text_lower or "mikropluostas" in text_lower:
        fabric_type = "Микрофибра"
    elif "flokas" in text_lower:
        fabric_type = "Флок"
    elif "natūrali oda" in text_lower or "naturali oda" in text_lower:
        fabric_type = "Натуральная кожа"
    elif "buklė" in text_lower or "boucle" in text_lower:
        fabric_type = "Букле"

    # 3. СВОЙСТВА (Словарь Литовский -> Русский)
    properties_list = []
    
    # Ищем упоминания в тексте или в названиях иконок в HTML
    combined_content = text_lower + " " + clean_html.lower()

    if "lengvai valom" in combined_content or "easy clean" in combined_content or "lengvas valymas" in combined_content:
        properties_list.append("Легкая чистка")
    
    # Проверка на Антикоготь (исключаем "nedraugiški")
    if ("draugišk" in combined_content or "pet friendly" in combined_content or "gyvūnams" in combined_content) and "nedraugišk" not in combined_content:
        properties_list.append("Антикоготь")
        
    if "vandeniui atsparus" in combined_content or "skysčius atstumiantis" in combined_content or "skysčius" in combined_content or "water repellent" in combined_content:
        properties_list.append("Водоотталкивающая")
        
    if "ugniai atsparus" in combined_content or "nedegus" in combined_content or "cigaretės testas" in combined_content or "fire retardant" in combined_content:
        properties_list.append("Огнеупорная")
        
    properties_str = ", ".join(properties_list) if properties_list else None

    return martindale, fabric_type, properties_str

async def fix_litena_data():
    db_path = 'fabrics.db'
    if not os.path.exists(db_path):
        print("База данных не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Выбираем ткани Litena для полного сканирования
    cursor.execute("SELECT id, name, product_url, martindale, fabric_type, properties FROM fabrics WHERE manufacturer LIKE '%Litena%' AND product_url IS NOT NULL AND product_url != ''")
    rows = cursor.fetchall()
    
    print(f"Найдено {len(rows)} тканей Litena для проверки типа, свойств и Мартиндейла.")

    updated_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        for idx, row in enumerate(rows):
            fid, name, url, old_martindale, old_type, old_props = row
            print(f"\n[{idx+1}/{len(rows)}] Проверка {name} - {url}")
            
            try:
                response = await page.goto(url, timeout=15000)
                if response is None or response.status >= 400:
                    print(f" -> Ошибка: страница недоступна (код {response.status if response else 'неизвестно'})")
                    continue
                    
                await asyncio.sleep(2)
                
                # Извлекаем и текст, и HTML (иногда свойства написаны в атрибутах title или alt картинок-иконок)
                text = await page.locator("body").inner_text()
                html = await page.locator("body").inner_html()
                
                new_martindale, parsed_type, parsed_props = extract_litena_data(text, html)
                
                # Обновляем только если нашли новые данные
                updates = []
                params = []
                
                if new_martindale and new_martindale != old_martindale:
                    updates.append("martindale = ?")
                    params.append(new_martindale)
                    
                if parsed_type and parsed_type != old_type:
                    updates.append("fabric_type = ?")
                    params.append(parsed_type)
                    
                if parsed_props and parsed_props != old_props:
                    updates.append("properties = ?")
                    params.append(parsed_props)
                    
                if updates:
                    params.append(fid)
                    sql = f"UPDATE fabrics SET {', '.join(updates)} WHERE id = ?"
                    cursor.execute(sql, tuple(params))
                    conn.commit()
                    updated_count += 1
                    print(f" -> ОБНОВЛЕНО!")
                    if new_martindale and new_martindale != old_martindale:
                        print(f"    * Мартиндейл: {new_martindale} (был {old_martindale})")
                    if parsed_type and parsed_type != old_type:
                        print(f"    * Тип: {parsed_type} (был {old_type})")
                    if parsed_props and parsed_props != old_props:
                        print(f"    * Свойства: {parsed_props} (были {old_props})")
                else:
                    print(" -> Новых данных не найдено или они совпадают с базой.")
                    if parsed_type: print(f"    (Найден тип: {parsed_type}, Мартиндейл: {new_martindale})")
                    
            except Exception as e:
                print(f" -> Ошибка при загрузке: {e}")

        await browser.close()
        
    print(f"\nПроверка завершена. Успешно обновлены данные для {updated_count} тканей Litena.")
    conn.close()

if __name__ == "__main__":
    asyncio.run(fix_litena_data())
