import os
import sys
import re
import asyncio

# Добавляем корневую директорию в sys.path, чтобы импортировать модели и БД
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from backend.database import SessionLocal
from backend.models import Fabric

DEDAR_PDF = os.path.join(ROOT_DIR, "Dedar Pricelist 2026 .pdf")
MARIAFLORA_PDF = os.path.join(ROOT_DIR, "MariaFlora Pricelist 2026.pdf")

def extract_from_pdf(pdf_path, manufacturer, limit=3):
    """
    Черновой парсер PDF: пытается извлечь таблицы и найти в них нужные данные.
    """
    extracted = []
    if not os.path.exists(pdf_path):
        print(f"[-] Файл не найден: {pdf_path}")
        return extracted
        
    try:
        import pdfplumber
        print(f"[*] Открываем PDF: {os.path.basename(pdf_path)}")
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row: continue
                        
                        # Очищаем ячейки от None
                        row_cleaned = [str(c).strip() if c else "" for c in row]
                        row_cleaned = [c for c in row_cleaned if c] # убираем пустые
                        if not row_cleaned: continue
                        
                        text_row = " ".join(row_cleaned).lower()
                        
                        # Пропускаем строки заголовков
                        if any(header in text_row for header in ["description", "item", "price", "code", "composition"]):
                            continue
                            
                        name = row_cleaned[0]
                        if len(name) < 3:
                            continue
                            
                        # Поиск цены (форматы: 100.50, 100,50)
                        price_match = re.search(r'(\d+[.,]\d+)\s*(?:€|eur)?', " ".join(row_cleaned), re.IGNORECASE)
                        price = 0.0
                        if price_match:
                            try:
                                price = float(price_match.group(1).replace(',', '.'))
                            except:
                                pass
                        
                        # Поиск свойств (перевод на русский)
                        properties = []
                        if "wr" in text_row or "in-outdoor" in text_row or "outdoor" in text_row:
                            properties.append("Водоотталкивание")
                        if "stain resistant" in text_row or "stain" in text_row:
                            properties.append("Легкая чистка")
                            
                        # Поиск Martindale (например: 40.000 или 40 000)
                        martindale_match = re.search(r'(\d{2,3}[\s.]?\d{3})', " ".join(row_cleaned))
                        martindale = 0
                        if martindale_match:
                            try:
                                martindale = int(re.sub(r'[^\d]', '', martindale_match.group(1)))
                            except:
                                pass
                                
                        item = {
                            "name": name.replace('\n', ' ').strip(),
                            "manufacturer": manufacturer,
                            "price": price,
                            "properties": ", ".join(properties) if properties else None,
                            "martindale": martindale if martindale > 0 else None,
                        }
                        
                        # Исключаем дубликаты
                        if not any(e['name'] == item['name'] for e in extracted):
                            extracted.append(item)
                            print(f"  -> Найдено в PDF: {item['name']} (Цена: {item['price']}, Martindale: {item['martindale']})")
                            
                        if len(extracted) >= limit:
                            return extracted
    except Exception as e:
        print(f"[-] Ошибка при чтении {pdf_path}: {e}")
        
    return extracted

async def scrape_dedar_fabric(page, name):
    """
    Скрейпинг картинок с сайта Dedar через Playwright.
    """
    print(f"[*] Поиск ткани на dedar.com: {name}")
    # Используем английскую версию поиска (чаще всего так надежнее)
    search_url = f"https://dedar.com/en/search?q={name}"
    
    try:
        await page.goto(search_url, timeout=15000)
        
        # Ждем загрузки результатов (ссылки на карточки продуктов)
        await page.wait_for_selector('.card-figure__link, .product-link', timeout=8000)
        product_element = page.locator('.card-figure__link, .product-link').first
        
        product_url = await product_element.get_attribute('href')
        if product_url and not product_url.startswith('http'):
            product_url = "https://dedar.com" + product_url
            
        print(f"  -> Найдена страница: {product_url}")
        
        # Переходим на страницу продукта
        await page.goto(product_url, timeout=15000)
        
        # Ищем главную картинку
        await page.wait_for_selector('.productView-image img', timeout=8000)
        image_element = page.locator('.productView-image img').first
        
        image_url = await image_element.get_attribute('src')
            
        if image_url and not image_url.startswith('http'):
            if image_url.startswith('//'):
                image_url = "https:" + image_url
            else:
                image_url = "https://dedar.com" + image_url
                
        print(f"  -> Найдено фото: {image_url}")
        return product_url, image_url
        
    except Exception as e:
        print(f"[-] Не удалось найти/спарсить на сайте: {name} ({e})")
        return None, None

def save_to_db(item):
    """
    Сохранение в базу SQLite через SQLAlchemy.
    """
    db = SessionLocal()
    try:
        existing = db.query(Fabric).filter(Fabric.name == item['name']).first()
        if existing:
            print(f"[*] Обновление {item['name']} в БД...")
            existing.price = item.get('price', existing.price)
            if item.get('martindale'):
                existing.martindale = item['martindale']
            if item.get('properties'):
                existing.properties = item['properties']
            existing.category = item.get('category', existing.category)
            if item.get('image_url'):
                existing.image_url = item['image_url']
            if item.get('product_url'):
                existing.product_url = item['product_url']
        else:
            print(f"[+] Добавление {item['name']} в БД...")
            fabric = Fabric(
                name=item['name'],
                manufacturer=item['manufacturer'],
                price=item.get('price'),
                martindale=item.get('martindale'),
                properties=item.get('properties'),
                category=item.get('category'),
                image_url=item.get('image_url'),
                product_url=item.get('product_url'),
                fabric_type="Другое",
                missing_price=False
            )
            db.add(fabric)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[-] Ошибка БД: {e}")
    finally:
        db.close()

async def main():
    print("=== ЭТАП 1: Парсинг PDF ===")
    dedar_items = extract_from_pdf(DEDAR_PDF, "Dedar", limit=3)
    maria_items = extract_from_pdf(MARIAFLORA_PDF, "Mariaflora", limit=3)
    
    all_items = dedar_items + maria_items
    if not all_items:
        print("[-] Не удалось извлечь данные из PDF. Проверьте пути к файлам и их формат.")
        return
        
    print(f"\n=== ЭТАП 2: Скрейпинг фото и запись в БД ({len(all_items)} тканей) ===")
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # headless=False чтобы было видно, как открывается браузер и ищутся ткани
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        for item in all_items:
            p_url, i_url = await scrape_dedar_fabric(page, item['name'])
            item['product_url'] = p_url
            item['image_url'] = i_url
            item['category'] = "Премиум"
            
            save_to_db(item)
            
            # Небольшая пауза между запросами, чтобы не забанили
            await asyncio.sleep(2)
            
        await browser.close()
        
    print("\n[+] Готово! Тестовый прогон завершен.")

if __name__ == "__main__":
    asyncio.run(main())
