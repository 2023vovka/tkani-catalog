import sqlite3
import asyncio
import os
from playwright.async_api import async_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, "fabrics.db")

async def scrape_davis_collections(max_pages=2):
    all_web_products = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"[*] Открываю каталог Davis Fabrics (Ограничение: {max_pages} страниц)...")
        await page.goto("https://www.davis.pl/en/collections/", timeout=60000)
        
        # Пытаемся закрыть попап с куки
        try: await page.click('.cookie-accept, #cookie_action_close_header', timeout=3000)
        except: pass
        
        page_num = 1
        while page_num <= max_pages:
            print(f"\n[~] Сканирую страницу {page_num}...")
            
            try:
                await page.wait_for_selector(".list__item", timeout=15000)
                await asyncio.sleep(2) # Даем подгрузиться
            except:
                print("[!] Карточки коллекций не найдены. Выход.")
                break
                
            cards = await page.query_selector_all(".list__item")
            print(f"    -> Найдено {len(cards)} коллекций на странице.")
            
            # 1. Собираем названия и ссылки на детальные страницы
            collection_links = []
            for card in cards:
                try:
                    link_elem = await card.query_selector(".list__object")
                    title_elem = await card.query_selector(".list__title a")
                    
                    if link_elem and title_elem:
                        href = await link_elem.get_attribute("href")
                        name = (await title_elem.inner_text()).strip().upper()
                        
                        if href and name:
                            if not href.startswith('http'):
                                href = "https://www.davis.pl" + href
                            collection_links.append((name, href))
                except Exception as e:
                    continue
                    
            print(f"    -> Начинаю обход внутрь {len(collection_links)} коллекций для поиска статических фото...")
            
            # 2. Проваливаемся в каждую коллекцию
            detail_page = await context.new_page()
            for name, url in collection_links:
                if name in all_web_products:
                    continue
                    
                print(f"       -> Захожу в {name}")
                try:
                    await detail_page.goto(url, timeout=30000)
                    await detail_page.wait_for_load_state("domcontentloaded")
                    
                    # Ищем качественную статичную картинку
                    # На странице Davis Fabrics качественные фото лежат в href атрибуте образцов цвета
                    img_url = ""
                    color_swatch = await detail_page.query_selector(".glightbox.product__colors__element")
                    
                    if color_swatch:
                        img_url = await color_swatch.get_attribute("href")
                        
                    # Запасной вариант - ищем большое изображение коллекции
                    if not img_url:
                        images = await detail_page.query_selector_all("img")
                        for img in images:
                            src = await img.get_attribute("src")
                            if not src:
                                src = await img.get_attribute("data-src")
                                
                            if src and (".jpg" in src.lower() or ".webp" in src.lower() or ".png" in src.lower()):
                                if "logo" not in src.lower() and "icon" not in src.lower():
                                    img_url = src
                                    break
                    
                    if img_url:
                        if not img_url.startswith('http'):
                            img_url = "https://www.davis.pl" + img_url
                        all_web_products[name] = {"image": img_url, "url": url}
                        print(f"          [OK] Найдено фото: {img_url.split('/')[-1]}")
                    else:
                        print(f"          [-] Фото не найдено")
                        
                except Exception as e:
                    print(f"          [!] Ошибка загрузки: {str(e)[:50]}")
                    continue
                    
            await detail_page.close()
            
            if page_num >= max_pages:
                break
                
            # 3. Переход на следующую страницу каталога
            target_page = page_num + 1
            next_btn = page.locator(f".list__pagination-btn[data-page='{target_page}']").first
            
            if await next_btn.is_visible():
                await next_btn.click()
                page_num += 1
                await asyncio.sleep(4)
            else:
                print("[!] Кнопка перехода на следующую страницу не найдена. Конец каталога.")
                break

        await browser.close()
        
    print(f"\n[*] Завершено сканирование. Найдено {len(all_web_products)} уникальных фото (Лимит: {max_pages} стр).")
    return all_web_products

async def update_database_images(web_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ищем ткани Davis в базе данных
    cursor.execute("SELECT id, name FROM fabrics WHERE manufacturer LIKE '%Davis%'")
    db_fabrics = cursor.fetchall()
    
    updated_count = 0
    print(f"\n[*] Начинаю сопоставление с базой данных ({len(db_fabrics)} тканей Davis)...")
    
    for fabric_id, db_name in db_fabrics:
        clean_db_name = db_name.split(' ')[0].upper()
        
        match_data = None
        for web_name, data in web_data.items():
            # Если имя базы совпадает с именем коллекции
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
    print(f"\n[+++] Готово! Обновлено тканей Davis: {updated_count}")

async def main():
    web_products = await scrape_davis_collections(max_pages=2)
    if web_products:
        await update_database_images(web_products)
    else:
        print("[-] Не удалось собрать товары с сайта.")

if __name__ == "__main__":
    asyncio.run(main())
