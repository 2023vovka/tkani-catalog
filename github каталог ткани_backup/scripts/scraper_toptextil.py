import asyncio
import sys
import os
import re
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import SessionLocal, engine, Base
from backend.models import Fabric, FabricColor

async def scrape_toptextil():
    db = SessionLocal()
    fabrics = db.query(Fabric).filter(Fabric.manufacturer.ilike('%Toptextil%')).all()
    print(f"Loaded {len(fabrics)} Toptextil fabrics from database.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for fabric in fabrics:
            try:
                # Guess the URL
                fabric_slug = re.sub(r'[^a-z0-9]', '-', fabric.name.strip().lower())
                fabric_slug = re.sub(r'-+', '-', fabric_slug).strip('-')
                url = f"https://www.toptextil.pl/en/collection/{fabric_slug}/"
                print(f"Fetching: {url}")
                
                response = await page.goto(url, timeout=30000)
                if response is None or response.status == 404:
                    print(f"Ткань {fabric.name} пропущена (404 Not Found)")
                    continue
                    
                await asyncio.sleep(1) # wait for DOM
                title = await page.title()
                if "404" in title or "not found" in title.lower() or "Page not found" in title:
                    print(f"Ткань {fabric.name} пропущена (404 page)")
                    continue
                    
                fabric.product_url = url

                # Tech specs
                try:
                    weight_el = page.locator("xpath=//div[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='weight']/following-sibling::div").first
                    weight_text = await weight_el.inner_text(timeout=2000)
                    if weight_text:
                        digits = re.findall(r'\d+', weight_text)
                        if digits:
                            fabric.density = int(digits[0])
                except Exception as e:
                    print(f"  [Ошибка] Не удалось получить плотность для {fabric.name}: {e}")
                
                try:
                    abrasion_el = page.locator("xpath=//div[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='abrasion resistance']/following-sibling::div").first
                    abrasion_text = await abrasion_el.inner_text(timeout=2000)
                    if abrasion_text:
                        digits = re.findall(r'\d+', abrasion_text.replace(' ', ''))
                        if digits:
                            fabric.martindale = int(digits[0])
                except Exception as e:
                    print(f"  [Ошибка] Не удалось получить мартиндейл для {fabric.name}: {e}")

                # Properties
                props = []
                try:
                    page_text = (await page.locator('body').text_content()).lower()
                    if any(x in page_text for x in ['water rep', 'liquid', 'spill', 'waterproof', 'hydro']):
                        props.append("water repellent")
                    if any(x in page_text for x in ['pet proof', 'petproof', 'pet friend', 'scratch', 'animal']):
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
                    color_elements = await page.locator("a.my-gallery-grid__image").all()
                    if not color_elements:
                        print(f"  [Предупреждение] На странице {url} картинки цветов не найдены! Идем дальше.")
                    else:
                        for i, col in enumerate(color_elements):
                            image_url = await col.get_attribute("href")
                            color_title = await col.inner_text()
                            color_title = color_title.strip() if color_title else f"{fabric.name} {i+1}"
                                
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
    asyncio.run(scrape_toptextil())
