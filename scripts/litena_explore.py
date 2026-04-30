import asyncio
from playwright.async_api import async_playwright

async def run():
    try:
        print("Starting Playwright...")
        async with async_playwright() as p:
            print("Launching browser in headed mode...")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("Navigating to Litena catalog...")
            # Use smaller timeout and wait until domcontentloaded to avoid hanging on external resources
            await page.goto("https://www.litena.lt/en/katalogas/", wait_until="domcontentloaded", timeout=30000)
            print("Page loaded. Extracting links...")
            
            urls = await page.locator("a").all()
            links_found = 0
            for u in urls:
                try:
                    href = await u.get_attribute("href")
                    txt = await u.inner_text()
                    if href and 'katalogas/' in href:
                        print(f"URL: {href} | Text: {txt.strip()}")
                        links_found += 1
                except Exception as eval_err:
                    print(f"Error evaluating link: {eval_err}")
            
            print(f"Total relevant links found: {links_found}")
            
            print("Saving HTML...")
            html = await page.content()
            with open('litena_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            print("Closing browser...")
            await browser.close()
            print("Success.")
            
    except Exception as e:
        print(f"CRITICAL ERROR in Playwright script: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Script was cancelled by user (Ctrl+C).")
    except Exception as e:
        print(f"Unhandled exception: {e}")
