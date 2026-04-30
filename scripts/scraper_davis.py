import asyncio
import sys
import os
import re
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import SessionLocal, engine, Base
from backend.models import Fabric, FabricColor

async def scrape_davis():
    db = SessionLocal()
    fabrics = db.query(Fabric).filter(Fabric.manufacturer.ilike('%Davis%')).all()
    print(f"Loaded {len(fabrics)} Davis fabrics from database.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for fabric in fabrics:
            try:
                # Guess the URL
                fabric_slug = re.sub(r'[^a-z0-9]', '-', fabric.name.strip().lower())
                fabric_slug = re.sub(r'-+', '-', fabric_slug).strip('-')
                url = f"https://www.davis.pl/en/collection/{fabric_slug}/"
                
                print(f"Fetching: {url}")
                response = await page.goto(url, timeout=30000)
                
                if response is None or response.status == 404:
                    print(f"Ткань {fabric.name} пропущена (404 Not Found)")
                    continue
                    
                await asyncio.sleep(1) # wait for DOM
                
                # Check for 404 in page context
                title = await page.title()
                if "404" in title or "not found" in title.lower():
                    print(f"Ткань {fabric.name} пропущена (404 page)")
                    continue
                    
                fabric.product_url = url
                
                # Tech specs
                try:
                    tech_elements = await page.locator(".product__technical__element").all()
                    for el in tech_elements:
                        label = await el.locator(".product__technical__label").text_content()
                        val = await el.locator(".product__technical__value").text_content()
                        if label and val:
                            label = label.lower()
                            if 'grammage' in label or 'weight' in label:
                                digits = re.findall(r'\d+', val)
                                if digits:
                                    fabric.density = int(digits[0])
                            elif 'martindale' in label:
                                val_clean = val.replace(' ', '').replace('>', '')
                                digits = re.findall(r'\d+', val_clean)
                                if digits:
                                    fabric.martindale = int(digits[0])
                except Exception as e:
                    print(f"  [Ошибка] Не удалось получить характеристики для {fabric.name}: {e}")
                
                # Properties
                try:
                    page_text = (await page.locator('body').text_content()).lower()
                    props = []
                    
                    if any(x in page_text for x in ['water rep', 'liquid', 'spill', 'waterbloc', 'hydro']):
                        props.append("water repellent")
                    if any(x in page_text for x in ['pet friend', 'petproof', 'scratch', 'animal']):
                        props.append("petproof")
                    if any(x in page_text for x in ['easy clean', 'cleanaboo', 'valomas']):
                        props.append("easy clean")
                    if any(x in page_text for x in ['recycled', 'polyester rec', 'eco friendly']):
                        props.append("recycled")
                        
                    if props:
                        fabric.properties = ", ".join(props)
                except Exception as e:
                    print(f"  [Ошибка] Не удалось получить свойства для {fabric.name}: {e}")
                
                # Colors
                try:
                    color_elements = await page.locator("a.product__colors__element").all()
                    if not color_elements:
                        print(f"  [Предупреждение] На странице {url} картинки цветов не найдены! Идем дальше.")
                    else:
                        for i, col in enumerate(color_elements):
                            color_title = await col.get_attribute("title")
                            image_url = await col.get_attribute("href")
                            
                            if not color_title:
                                color_title = f"{fabric.name} {i+1}"
                                
                            if image_url:
                                if i == 0:
                                    fabric.image_url = image_url
                                existing_color = db.query(FabricColor).filter(FabricColor.fabric_id == fabric.id, FabricColor.color_name == color_title).first()
                                if not existing_color:
                                    new_color = FabricColor(fabric_id=fabric.id, color_name=color_title, image_url=image_url)
                                    db.add(new_color)
                                else:
                                    existing_color.image_url = image_url
                except Exception as e:
                    print(f"  [Ошибка] Ошибка при парсинге цветов для {fabric.name}: {e}")
                
                db.commit()
                print(f"Ткань {fabric.name} — обработана успешно (URL и данные сохранены).")
                
            except Exception as e:
                print(f"Ткань {fabric.name} пропущена (критическая ошибка: {e})")
                db.rollback()

        await browser.close()
    db.close()

if __name__ == "__main__":
    asyncio.run(scrape_davis())
