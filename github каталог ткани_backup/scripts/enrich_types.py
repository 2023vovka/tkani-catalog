import sqlite3
import sys
import os

# Ensure column exists
try:
    conn = sqlite3.connect("fabrics.db")
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE fabrics ADD COLUMN fabric_type VARCHAR DEFAULT 'Другое'")
    conn.commit()
    conn.close()
    print("Column fabric_type added to database.")
except Exception as e:
    print("Column may already exist:", e)

# Setup path and db session
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import SessionLocal
from backend.models import Fabric

TYPE_MAP = {
    'Велюр / Микровелюр': ['suede', 'velvet', 'casablanca', 'magic', 'dream', 'monolith', 'matt', 'kongo', 'riviera', 'eureka', 'dizzy', 'cloud', 'royal', 'solo', 'amore', 'jasmine', 'krona', 'piano', 'palladium', 'tilia', 'fancy', 'nube', 'storm', 'nadir', 'belisimo', 'faro'],
    'Рогожка': ['runo', 'braid', 'woven', 'boston', 'berlin', 'paris', 'nepal', 'inari', 'luna', 'gobi', 'hugo', 'bison', 'bizon', 'ibiza', 'eterna', 'kendo', 'porto', 'tokyo', 'milan', 'toronto'],
    'Шенилл': ['chenille', 'alvaro', 'palermo', 'dot', 'mirabel', 'loris', 'gelato', 'amadeo', 'livorno', 'silencio', 'versal', 'jartan', 'aragon', 'terra', 'dino'],
    'Букле': ['boucle', 'bukle', 'ascot', 'now or never', 'catch me', 'coco', 'neve', 'baloo', 'curly', 'teddy', 'barbie', 'marcos'],
    'Экокожа': ['leather', 'eko', 'cayenne', 'madryt', 'madrid', 'vienna', 'texas', 'florida', 'caro', 'santos', 'soft', 'fusion'],
    'Трикотаж': ['knit', 'knitted', 'terry', 'onda', 'pico', 'aldo']
}

def determine_type(name, category, properties):
    text = f"{name} {category or ''} {properties or ''}".lower()
    
    # 1. Check exact keywords from our curated dictionary
    for t_name, keywords in TYPE_MAP.items():
        for kw in keywords:
            if kw in text:
                return t_name
            
    # 2. General broad matching fallback
    if 'velvet' in text or 'велюр' in text:
        return 'Велюр / Микровелюр'
    if 'chenille' in text or 'шенилл' in text:
        return 'Шенилл'
    if 'braid' in text or 'woven' in text or 'рогожка' in text:
        return 'Рогожка'
    if 'boucle' in text or 'букле' in text:
        return 'Букле'
    if 'leather' in text or 'кожа' in text:
        return 'Экокожа'
    if 'knit' in text or 'трикотаж' in text:
        return 'Трикотаж'

    return 'Другое'

def enrich_properties(name, category, properties):
    text = f"{name} {category or ''} {properties or ''}".lower()
    
    tags = set()
    
    water_kws = ['water', 'liquid', 'repellent', 'hydro', 'cleanaboo', 'vandeni']
    pet_kws = ['pet', 'scratch', 'animal', 'gyvun', 'petproof']
    clean_kws = ['clean', 'wash', 'easy', 'valomas']
    recycled_kws = ['recycled', ' eco ', ' eco-', 'perdirb']
    
    if any(kw in text for kw in water_kws):
        tags.add('Водоотталкивание')
    if any(kw in text for kw in pet_kws):
        tags.add('Антикоготь')
    if any(kw in text for kw in clean_kws):
        tags.add('Легкая чистка')
    if any(kw in text for kw in recycled_kws):
        # Prevent "eco" from matching inside "ecological" if it's leather? 
        # Actually 'eko' is leather, 'eco' is recycled?
        # User defined: "eco" -> recycled. We will follow user definitions.
        tags.add('Переработанный полиэстер')
        
    return ", ".join(sorted(list(tags))) if tags else None

if __name__ == "__main__":
    db = SessionLocal()
    fabrics = db.query(Fabric).all()
    updated = 0
    
    for f in fabrics:
        new_type = determine_type(f.name, f.category, f.properties)
        f.fabric_type = new_type
        
        new_props = enrich_properties(f.name, f.category, f.properties)
        f.properties = new_props
        
        updated += 1
        
    db.commit()
    print(f"✅ Успешно обогащено тканей (AI Dictionary + Свойства): {updated}")
