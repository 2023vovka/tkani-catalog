import sys
import os
import pandas as pd

# Add parent directory to sys.path to resolve 'backend' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine, Base
from backend.models import Fabric

def parse_price(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except:
        return None

def main():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Ткани база.xlsx')
    if not os.path.exists(excel_path):
        print(f"Excel file not found at {excel_path}")
        return

    print("Loading Excel...")
    df = pd.read_excel(excel_path)
    
    added_count = 0
    for index, row in df.iterrows():
        name = str(row.get('Наименование', '')).strip()
        if not name or pd.isna(name) or name == 'nan':
            continue
            
        manufacturer = str(row.get('Производитель', '')).strip()
        category = str(row.get('Категория', '')).strip()
        
        retail = parse_price(row.get('Цена*'))
        wholesale = parse_price(row.get('Unnamed: 8'))
        
        props_str = str(row.get('Свойства', ''))
        
        density = row.get('Плотность')
        # Try to clean density
        try:
            density_val = int(str(density).replace('g/m2','').replace('г/м2','').strip())
        except:
            density_val = None
            
        martindale = row.get('Мартиндейл')
        try:
            martindale_val = int(str(martindale).replace(' ', '').replace('>', ''))
        except:
            martindale_val = None

        fabric = db.query(Fabric).filter(Fabric.name == name, Fabric.manufacturer == manufacturer).first()
        
        if not fabric:
            fabric = Fabric(
                name=name,
                manufacturer=manufacturer,
                category=category,
                price=retail,
                wholesale_price=wholesale,
                missing_price=(retail is None),
                density=density_val,
                martindale=martindale_val,
                properties=props_str
            )
            db.add(fabric)
            added_count += 1
        else:
            # Update price if it exists in excel
            if retail is not None:
                fabric.price = retail
                fabric.missing_price = False
            if wholesale is not None:
                fabric.wholesale_price = wholesale

    db.commit()
    db.close()
    print(f"Successfully imported {added_count} fabrics from Excel.")

if __name__ == "__main__":
    main()
