import asyncio
import os
import re
from playwright.async_api import async_playwright

async def probe_toptextil():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        test_url = "https://www.toptextil.pl/en/collection/ancona-anti-slip-9940/"
        print(f"--- PROBE COLLECTION: {test_url} ---")
        await page.goto(test_url, timeout=60000)
        await asyncio.sleep(2) # Wait for page rendering
        
        html = await page.content()
        with open("ancona_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # density
        
        # martindale
        martindale = None
        try:
            abrasion_el = page.locator("xpath=//div[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='abrasion resistance']/following-sibling::div").first
            abrasion_text = await abrasion_el.inner_text()
            if abrasion_text:
                digits = re.findall(r'\d+', abrasion_text.replace(' ', ''))
                if digits:
                    martindale = int(digits[0])
        except Exception as e: pass
        
        # properties
        props = []
        try:
            content_text = await page.content()
            content_low = content_text.lower()
            if 'water repellent' in content_low or 'liquid blocked' in content_low or 'waterproof' in content_low or 'water blocked' in content_low:
                props.append("Водоотталкивание")
            if 'pet proof' in content_low or 'pet friendly' in content_low:
                props.append("Для животных")
            if 'cleanaboo' in content_low or 'easy clean' in content_low:
                props.append("Легкая чистка")
        except: pass
        
        # colors
        colors = []
        try:
            color_elements = await page.locator("a.my-gallery-grid__image").all()
            for i, col in enumerate(color_elements):
                if i >= 5: # just get 5 for demo
                    break
                image_url = await col.get_attribute("href")
                color_title = await col.inner_text()
                colors.append({"name": color_title.strip() if color_title else f"Color {i+1}", "img": os.path.basename(image_url) if image_url else None})
        except: pass
        
        print(f"Density: {density} g/m2")
        print(f"Martindale: {martindale} cycles")
        print(f"Properties: {', '.join(props)}")
        print(f"Colors (first 5): {colors}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(probe_toptextil())
