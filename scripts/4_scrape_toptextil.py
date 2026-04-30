import sqlite3
import asyncio
import os
from playwright.async_api import async_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, "fabrics.db")

async def scrape_toptextil():
    all_web_products = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("[*] Открываю каталог Toptextil...")
        await page.goto("https://www.toptextil.pl/en/fabrics/", timeout=60000)
        
        # Пытаемся закрыть попап с куки
        try: await page.click('.cli-plugin-button, #cookie_action_close_header, .cookie-accept', timeout=3000)
        except: pass
        
        try:
            await page.wait_for_selector(".fabrics-block__loop__element", timeout=15000)
        except:
            print("[!] Не удалось дождаться загрузки карточек Toptextil.")
            await browser.close()
            return all_web_products
            
        print("[*] Начинаю скролл и поиск товаров. Сайт использует динамическую подгрузку...")
        last_height = 0
        scroll_attempts = 0
        
        while True:
            # Скроллим вниз постепенно
            await page.evaluate("window.scrollBy(0, 1500)")
            await asyncio.sleep(1.5)
            
            # Собираем всё, что уже отрендерилось
            cards = await page.query_selector_all(".fabrics-block__loop__element")
            for card in cards:
                try:
                    name_elem = await card.query_selector(".fabrics-block__loop__element__title .brxe-text-basic")
                    if name_elem:
                        name = (await name_elem.inner_text()).strip().upper()
                        href = await card.get_attribute("href")
                        
                        img_url = ""
                        # Ищем статичную картинку, видео игнорируем
                        img_elem = await card.query_selector("figure img")
                        if img_elem:
                            img_url = await img_elem.get_attribute("src")
                            if not img_url:
                                img_url = await img_elem.get_attribute("data-src")
                                
                        if img_url and name not in all_web_products:
                            if not img_url.startswith('http'):
                                img_url = "https://www.toptextil.pl" + img_url
                            if href and not href.startswith('http'):
                                href = "https://www.toptextil.pl" + href
                                
                            all_web_products[name] = {"image": img_url, "url": href}
                except:
                    continue
                    
            print(f"[+] Собрано тканей: {len(all_web_products)}", end="\r")
            
            # Если есть кнопка "Load more" (на всякий случай)
            try:
                load_more = page.locator("text='Load more', text='Show more', .load-more, .brxe-button").locator("visible=true").first
                if await load_more.count() > 0:
                    await load_more.click()
                    await asyncio.sleep(2)
            except: pass
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
                if scroll_attempts > 5: # Ждем 5 попыток, вдруг сеть тупит
                    print("\n[!] Достигнут конец каталога (высота страницы не меняется).")
                    break
            else:
                scroll_attempts = 0
                last_height = new_height

        await browser.close()
        
    print(f"\n[*] Завершено сканирование. Найдено {len(all_web_products)} уникальных фото Toptextil.")
    return all_web_products

async def update_database_images(web_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ищем ткани Toptextil в базе данных
    cursor.execute("SELECT id, name FROM fabrics WHERE manufacturer LIKE '%Toptextil%'")
    db_fabrics = cursor.fetchall()
    
    updated_count = 0
    print(f"\n[*] Начинаю сопоставление с базой данных ({len(db_fabrics)} тканей Toptextil)...")
    
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
    print(f"\n[+++] Готово! Обновлено тканей Toptextil: {updated_count}")

async def main():
    web_products = await scrape_toptextil()
    if web_products:
        await update_database_images(web_products)
    else:
        print("[-] Не удалось собрать товары с сайта Toptextil.")

if __name__ == "__main__":
    asyncio.run(main())
