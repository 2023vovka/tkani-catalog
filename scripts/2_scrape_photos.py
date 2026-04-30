import sqlite3
import asyncio
import os
from playwright.async_api import async_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, "fabrics.db")

async def scrape_all_dedar_products():
    all_web_products = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("[*] Открываю каталог всех продуктов Dedar (Надежная пагинация по URL)...")
        
        page_num = 1
        while True:
            # Для первой страницы используем чистый URL, для остальных добавляем ?page=
            if page_num == 1:
                url = "https://dedar.com/products/"
            else:
                url = f"https://dedar.com/products/?page={page_num}"
                
            print(f"[~] Сканирую страницу {page_num}: {url}")
            
            try:
                await page.goto(url, timeout=60000)
                # Ждем загрузки именно карточек товара
                await page.wait_for_selector(".product-card, .product-item, .card, article, .ais-Hits-item", timeout=15000)
                # Небольшая пауза, чтобы скрипты сайта успели подтянуть картинки
                await asyncio.sleep(3) 
            except:
                print(f"[!] Карточки не найдены на странице {page_num}. Завершаем обход.")
                break
                
            cards = await page.query_selector_all(".product-card, .product-item, .card, article, .ais-Hits-item")
            
            # Если карточек 0, значит страницы закончились
            if len(cards) == 0:
                print(f"[!] Пустая страница {page_num}. Конец каталога.")
                break

            added_on_page = 0
            
            for card in cards:
                try:
                    name_elem = await card.query_selector(".product-card__title, .product-title, h3, .card-title")
                    if name_elem:
                        name = (await name_elem.inner_text()).strip().upper()
                        
                        # 1. Извлекаем картинку (оказалось, они в скрытой кнопке moodboard)
                        img_url = ""
                        moodboard_btn = await card.query_selector(".btn-add-product-to-moodboard")
                        if moodboard_btn:
                            img_url = await moodboard_btn.get_attribute("data-src")
                            if img_url:
                                img_url = img_url.replace("{:size}", "1280x1280") # Подтягиваем высокое качество
                                
                        if not img_url: # Запасной план
                            img_fallback = await card.query_selector(".card-img-container")
                            if img_fallback:
                                style = await img_fallback.get_attribute("style")
                                if style and "url(" in style:
                                    img_url = style.split("url(")[1].split(")")[0].strip("\"'")

                        # 2. Извлекаем прямую ссылку на товар
                        link_elem = await card.query_selector(".product-link, .card-figure__link")
                        product_url = ""
                        if link_elem:
                            product_url = await link_elem.get_attribute("href")
                            
                        # Приводим ссылки в нормальный вид
                        if img_url and img_url.startswith('/'): img_url = "https://dedar.com" + img_url
                        elif img_url and img_url.startswith('//'): img_url = "https:" + img_url
                            
                        if product_url and product_url.startswith('/'): product_url = "https://dedar.com" + product_url
                        elif product_url and product_url.startswith('//'): product_url = "https:" + product_url
                        
                        if img_url and name not in all_web_products:
                            all_web_products[name] = {"image": img_url, "url": product_url}
                            added_on_page += 1
                except:
                    continue
                    
            print(f"    -> Найдено новых товаров: {added_on_page}. Всего собрано: {len(all_web_products)}")
            
            # Если на странице вообще не добавилось новых товаров (например, сайт начал выдавать одно и то же)
            if added_on_page == 0:
                print("[!] На странице нет новых товаров. Завершаем цикл.")
                break

            page_num += 1

        await browser.close()
        
    print(f"\n[*] Завершено сканирование. Найдено {len(all_web_products)} уникальных фото.")
    return all_web_products

async def update_database_images(web_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM fabrics WHERE manufacturer IN ('Dedar', 'Mariaflora')")
    db_fabrics = cursor.fetchall()
    
    updated_count = 0
    print(f"\n[*] Начинаю сопоставление с базой данных ({len(db_fabrics)} тканей без фото)...")
    
    for fabric_id, db_name in db_fabrics:
        clean_db_name = db_name.split(' ')[0].upper()
        
        match_data = None
        for web_name, data in web_data.items():
            if clean_db_name in web_name:
                match_data = data
                break
        
        if match_data:
            cursor.execute("UPDATE fabrics SET image_url = ?, product_url = ? WHERE id = ?", 
                           (match_data["image"], match_data["url"], fabric_id))
            updated_count += 1
            print(f"    [OK] Найдено фото для: {db_name}")

    conn.commit()
    conn.close()
    print(f"\n[+++] Готово! Обновлено тканей: {updated_count}")

async def main():
    web_products = await scrape_all_dedar_products()
    if web_products:
        await update_database_images(web_products)
    else:
        print("[-] Не удалось собрать товары с сайта.")

if __name__ == "__main__":
    asyncio.run(main())
