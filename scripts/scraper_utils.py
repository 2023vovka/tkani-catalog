import os
import aiohttp
import asyncio

async def download_image(url, filename, save_dir):
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        filepath = os.path.join(save_dir, filename)
        if os.path.exists(filepath):
            return filepath
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return filepath
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None
