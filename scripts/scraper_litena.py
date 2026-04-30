import asyncio
import sys
import os
import re
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import SessionLocal, engine, Base
from backend.models import Fabric, FabricColor

async def scrape_litena():
    db = SessionLocal()
    fabrics = db.query(Fabric).filter(Fabric.manufacturer.ilike('%Litena%')).all()
    print(f"Loaded {len(fabrics)} Litena fabrics from database.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for fabric in fabrics:
            try:
                fabric_slug = re.sub(r'[^a-z0-9]', '-', fabric.name.strip().lower())
                fabric_slug = re.sub(r'-+', '-', fabric_slug).strip('-')
                
                # Ищем базовую ткань через поиск на Litena
                search_url = f"https://www.litena.lt/audiniu-paieska/?_search={fabric_slug}"
                print(f"Fetching search: {search_url}")
                
                response = await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2) # Wait for AJAX grid Bricks builder
                
                # Colors / Variants
                try:
                    product_links = await page.locator("a").all()
                    first_variant_url = None
                    colors_added = 0
                    
                    for l in product_links:
                        href = await l.get_attribute("href")
                        if href and f"/product/{fabric_slug}" in href.lower():
                            if not first_variant_url:
                                first_variant_url = href
                                
                            img_locators = await l.locator("img").all()
                            if img_locators:
                                img = img_locators[0]
                                data_src = await img.get_attribute("data-src")
                                data_srcset = await img.get_attribute("data-srcset")
                                fallback_src = await img.get_attribute("src")
                                
                                image_url = data_src or fallback_src
                                if data_srcset:
                                    image_url = data_srcset.split(',')[0].split(' ')[0]
                                
                                if image_url and ('.jpg' in image_url.lower() or '.png' in image_url.lower() or '.jpeg' in image_url.lower() or '.webp' in image_url.lower()):
                                    # Название цвета берем из URL продукта (например, /product/alpine-19/ -> Alpine 19)
                                    color_name = href.strip("/").split("/")[-1].replace("-", " ").title()
                                    
                                    if colors_added == 0:
                                        fabric.image_url = image_url
                                        fabric.product_url = href
                                        
                                    existing_color = db.query(FabricColor).filter(FabricColor.fabric_id == fabric.id, FabricColor.color_name == color_name).first()
                                    if not existing_color:
                                        new_color = FabricColor(fabric_id=fabric.id, color_name=color_name, image_url=image_url)
                                        db.add(new_color)
                                    else:
                                        existing_color.image_url = image_url
                                        
                                    colors_added += 1
                                    
                    if colors_added == 0:
                        print(f"  [Предупреждение] На странице поиска {search_url} товары-результаты не найдены!")
                except Exception as e:
                    print(f"  [Ошибка] Ошибка при парсинге цветов (результатов поиска) для {fabric.name}: {e}")
                    first_variant_url = None
                
                # Tech specs
                if first_variant_url:
                    try:
                        await page.goto(first_variant_url, wait_until="domcontentloaded", timeout=15000)
                        content_text = await page.content()
                        content_low = content_text.lower()
                        
                        weight_match = re.search(r'weight[^0-9]*(\d+)\s*g/m', content_low)
                        if weight_match:
                            fabric.density = int(weight_match.group(1))
                            
                        martindale_match = re.search(r'martindale[^0-9]*(\d{4,})', content_low)
                        if martindale_match:
                            fabric.martindale = int(martindale_match.group(1).replace(' ', ''))
                    except Exception as e:
                        print(f"  [Ошибка] Не удалось получить характеристики со страницы товара {fabric.name}: {e}")
                        
                db.commit()
                print(f"Ткань {fabric.name} — обработана успешно (URL и данные сохранены).")
                
            except Exception as e:
                print(f"Ткань {fabric.name} пропущена (критическая ошибка: {e})")
                db.rollback()

        await browser.close()
    db.close()

if __name__ == "__main__":
    asyncio.run(scrape_litena())
