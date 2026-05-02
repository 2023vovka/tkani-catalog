import sqlite3
import asyncio
import os
from playwright.async_api import async_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, "fabrics.db")

async def scrape_litena():
    all_web_products = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("[*] Открываю каталог Litena (audiniu-paieska)...")
        await page.goto("https://www.litena.lt/audiniu-paieska/", timeout=60000)
        
        # Пытаемся закрыть попап с куки, если есть
        try: await page.click('.cookie-notice-btn, #cookie_action_close_header, .accept-cookies', timeout=3000)
        except: pass
        
        try:
            await page.wait_for_selector("a.brxe-block", timeout=15000)
        except:
            print("[!] Не удалось дождаться загрузки карточек Litena.")
            await browser.close()
            return all_web_products
            
        print("[*] Начинаю обход каталога. Сайт использует кнопку 'Rodyti daugiau' (Load More)...")
        
        while True:
            # Сначала прокрутим немного вниз, чтобы подгрузились картинки и кнопка
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight - 1000)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)
            
            # Собираем видимые карточки
            cards = await page.query_selector_all("a.brxe-block")
            for card in cards:
                try:
                    name_elem = await card.query_selector("h6")
                    if name_elem:
                        name = (await name_elem.inner_text()).strip().upper()
                        href = await card.get_attribute("href")
                        
                        img_url = ""
                        img_elem = await card.query_selector("figure img")
                        if img_elem:
                            img_url = await img_elem.get_attribute("src")
                            if not img_url:
                                img_url = await img_elem.get_attribute("data-src")
                                
                        if img_url and name and name not in all_web_products:
                            if not img_url.startswith('http'):
                                img_url = "https://www.litena.lt" + img_url
                            if href and not href.startswith('http'):
                                href = "https://www.litena.lt" + href
                                
                            all_web_products[name] = {"image": img_url, "url": href}
                except:
                    continue
                    
            print(f"[+] Собрано тканей: {len(all_web_products)}", end="\r")
            
            # Ищем кнопку "Load more"
            try:
                load_more = page.locator(".wpgb-load-more").first
                if await load_more.is_visible():
                    await load_more.click()
                    await asyncio.sleep(3) # Ждем подгрузки новой порции
                else:
                    print("\n[!] Кнопка 'Load more' больше не видима. Достигнут конец каталога.")
                    break
            except Exception as e:
                print(f"\n[!] Конец каталога (кнопка исчезла).")
                break

        await browser.close()
        
    print(f"\n[*] Завершено сканирование. Найдено {len(all_web_products)} уникальных фото Litena.")
    return all_web_products

async def update_database_images(web_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ищем ткани Litena в базе данных
    cursor.execute("SELECT id, name FROM fabrics WHERE manufacturer LIKE '%Litena%'")
    db_fabrics = cursor.fetchall()
    
    updated_count = 0
    print(f"\n[*] Начинаю сопоставление с базой данных ({len(db_fabrics)} тканей Litena)...")
    
    for fabric_id, db_name in db_fabrics:
        clean_db_name = db_name.split(' ')[0].upper()
        
        match_data = None
        for web_name, data in web_data.items():
            if clean_db_name in web_name or web_name in clean_db_name:
                match_data = data
                break
        
        if match_data:
            cursor.execute("UPDATE fabrics SET image_url = ?, product_url = ? WHERE id = ?", 
                           (match_data["image"], match_data["url"], fabric_id))
            updated_count += 1
            print(f"    [OK] Обновлено фото для: {db_name}")

    conn.commit()
    conn.close()
    print(f"\n[+++] Готово! Обновлено тканей Litena: {updated_count}")

async def main():
    web_products = await scrape_litena()
    if web_products:
        await update_database_images(web_products)
    else:
        print("[-] Не удалось собрать товары с сайта Litena.")

if __name__ == "__main__":
    asyncio.run(main())
