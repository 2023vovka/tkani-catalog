import os
import sys
import pandas as pd
import asyncio
import sqlite3
from playwright.async_api import async_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_EXCEL = os.path.join(ROOT_DIR, "Ткани база.xlsx")
NEW_EXCEL = os.path.join(ROOT_DIR, "Новые_Ткани_Каталог.xlsx")
DB_PATH = os.path.join(ROOT_DIR, "fabrics.db")

# Добавляем корень для импорта модулей
sys.path.insert(0, ROOT_DIR)
from backend.database import SessionLocal, engine, Base
from backend.models import Fabric

def parse_price(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except:
        return None

def merge_excel_and_import():
    print("=== 1. Объединение Excel таблиц ===")
    if not os.path.exists(NEW_EXCEL):
        print("Файл Новые_Ткани_Каталог.xlsx не найден!")
        return
        
    # Читаем обе таблицы
    df_main = pd.read_excel(MAIN_EXCEL)
    df_new = pd.read_excel(NEW_EXCEL)
    
    # Объединяем и удаляем дубликаты
    df_combined = pd.concat([df_main, df_new], ignore_index=True)
    df_combined.drop_duplicates(subset=["Наименование", "Производитель"], inplace=True)
    
    # Перезаписываем основной файл
    df_combined.to_excel(MAIN_EXCEL, index=False)
    print(f"[+] Новые ткани успешно добавлены в {MAIN_EXCEL}")
    
    print("\n=== 2. Импорт в базу данных fabrics.db ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    added_count = 0
    updated_count = 0
    for index, row in df_combined.iterrows():
        name = str(row.get('Наименование', '')).strip()
        if not name or pd.isna(name) or name == 'nan':
            continue
            
        manufacturer = str(row.get('Производитель', '')).strip()
        category = str(row.get('Категория', '')).strip()
        
        retail = parse_price(row.get('Цена*'))
        wholesale = parse_price(row.get('Unnamed: 8'))
        
        props_str = str(row.get('Свойства', ''))
        
        density = row.get('Плотность')
        try: density_val = int(str(density).replace('g/m2','').replace('г/м2','').strip())
        except: density_val = None
            
        martindale = row.get('Мартиндейл')
        try: martindale_val = int(str(martindale).replace(' ', '').replace('>', ''))
        except: martindale_val = None

        fabric = db.query(Fabric).filter(Fabric.name == name, Fabric.manufacturer == manufacturer).first()
        
        if not fabric:
            fabric = Fabric(
                name=name, manufacturer=manufacturer, category=category,
                price=retail, wholesale_price=wholesale, missing_price=(retail is None),
                density=density_val, martindale=martindale_val,
                properties=props_str
            )
            db.add(fabric)
            added_count += 1
        else:
            updated = False
            if retail is not None and fabric.price != retail:
                fabric.price = retail
                fabric.missing_price = False
                updated = True
            if wholesale is not None and fabric.wholesale_price != wholesale:
                fabric.wholesale_price = wholesale
                updated = True
            if updated:
                updated_count += 1
                
    db.commit()
    db.close()
    print(f"[+] Импорт завершен. Добавлено: {added_count}, Обновлено: {updated_count}")

async def scrape_all_dedar_products(page):
    print("[*] Открываю каталог всех продуктов Dedar...")
    await page.goto("https://dedar.com/en/products/", timeout=60000)
    
    # Пытаемся закрыть попап с куки
    try: await page.click('button:has-text("Accept")', timeout=3000)
    except: pass
    
    # Ждем загрузки первых карточек
    await page.wait_for_selector(".product-card, .product-item, .card, article", timeout=15000)
    
    all_web_products = {}
    print("[*] Начинаю прокрутку каталога для загрузки всех товаров (это займет пару минут)...")
    
    last_height = 0
    while True:
        # Собираем данные
        cards = await page.query_selector_all(".product-card, .product-item, .card, article")
        for card in cards:
            try:
                name_elem = await card.query_selector(".product-card__title, .product-title, h3, .card-title")
                img_elem = await card.query_selector("img")
                
                if name_elem and img_elem:
                    name = (await name_elem.inner_text()).strip().upper()
                    img_url = await img_elem.get_attribute("src")
                    
                    if img_url and name not in all_web_products:
                        if img_url.startswith('/'):
                            img_url = "https://dedar.com" + img_url
                        elif img_url.startswith('//'):
                            img_url = "https:" + img_url
                        all_web_products[name] = img_url
            except:
                continue

        # Скроллим вниз
        await page.evaluate("window.scrollBy(0, 1500)")
        await asyncio.sleep(1.5)
        
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            await asyncio.sleep(3)
            if await page.evaluate("document.body.scrollHeight") == last_height:
                break
        last_height = new_height
        print(f"[+] Собрано товаров с сайта: {len(all_web_products)}", end="\r")

    print(f"\n[*] Завершено сканирование. Найдено {len(all_web_products)} уникальных фото.")
    return all_web_products

async def scrape_photos():
    print("\n=== 3. Загрузка фотографий с сайта Dedar ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name FROM fabrics 
        WHERE manufacturer IN ('Dedar', 'Mariaflora') AND (image_url IS NULL OR image_url = '')
    """)
    db_fabrics = cursor.fetchall()
    
    if not db_fabrics:
        print("[+] Все фотографии уже загружены в базу!")
        conn.close()
        return
        
    print(f"[*] Тканей без фото: {len(db_fabrics)}. Собираем базу с сайта...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        web_products = await scrape_all_dedar_products(page)
        await browser.close()
        
    print(f"\n[*] Начинаю сопоставление с базой данных...")
    updated_count = 0
    
    for fabric_id, db_name in db_fabrics:
        clean_db_name = db_name.split(' ')[0].upper()
        
        match_url = None
        for web_name, img_url in web_products.items():
            if clean_db_name in web_name:
                match_url = img_url
                break
        
        if match_url:
            cursor.execute("UPDATE fabrics SET image_url = ? WHERE id = ?", (match_url, fabric_id))
            updated_count += 1
            print(f"    [OK] Найдено фото для: {db_name}")

    conn.commit()
    conn.close()
    print(f"\n[+++] Готово! Обновлено тканей: {updated_count}")

def main():
    merge_excel_and_import()
    asyncio.run(scrape_photos())

if __name__ == "__main__":
    main()
