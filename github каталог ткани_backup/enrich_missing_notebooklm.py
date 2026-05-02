import sqlite3
import csv
import os

def enrich_and_export():
    db_path = 'fabrics.db'
    if not os.path.exists(db_path):
        print("База данных не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Извлекаем все ткани
    cursor.execute("SELECT id, name, manufacturer, category, price, density, martindale, properties, fabric_type FROM fabrics")
    rows = cursor.fetchall()

    updated_count = 0

    for row in rows:
        fid, name, manufacturer, category, price, density, martindale, properties, fabric_type = row
        name_lower = name.lower() if name else ""
        
        new_density = density
        new_martindale = martindale
        new_properties = properties
        new_fabric_type = fabric_type

        # --- 1. Логика для Мартиндейла (Износостойкость) ---
        if not new_martindale or new_martindale == 0:
            if 'velvet' in name_lower or 'велюр' in name_lower or 'adamo' in name_lower:
                new_martindale = 100000
            elif 'outdoor' in name_lower or 'улич' in name_lower:
                new_martindale = 60000
            elif manufacturer == 'Litena':
                new_martindale = 80000
            elif manufacturer == 'Dedar':
                new_martindale = 40000 # Жаккарды премиум сегмента
            elif manufacturer == 'Toptextil':
                new_martindale = 50000
            elif manufacturer == 'Davis':
                new_martindale = 60000
            else:
                new_martindale = 50000
                
        # --- 2. Логика для Плотности (г/м2) ---
        if not new_density or new_density == 0:
            if manufacturer == 'Litena':
                new_density = 380
            elif manufacturer == 'Dedar':
                new_density = 450
            elif manufacturer == 'Toptextil':
                new_density = 320
            elif manufacturer == 'Davis':
                new_density = 330
            else:
                new_density = 350
                
        # --- 3. Логика для Типа ткани ---
        if not new_fabric_type or new_fabric_type == 'Другое':
            if any(x in name_lower for x in ['velvet', 'велюр', 'suede', 'adamo', 'amore', 'solo']):
                new_fabric_type = 'Велюр / Микровелюр'
            elif any(x in name_lower for x in ['outdoor', 'sunlight']):
                new_fabric_type = 'Уличная ткань'
            elif any(x in name_lower for x in ['boucle', 'букле', 'baloo']):
                new_fabric_type = 'Букле'
            elif any(x in name_lower for x in ['chenille', 'шенилл', 'dino', 'palermo']):
                new_fabric_type = 'Шенилл'
            elif any(x in name_lower for x in ['eko', 'eco', 'кожа', 'madrid', 'madryt', 'leather']):
                new_fabric_type = 'Экокожа'
            elif any(x in name_lower for x in ['braid', 'woven', 'рогожка', 'porto', 'paris']):
                new_fabric_type = 'Рогожка'
            elif manufacturer == 'Dedar':
                new_fabric_type = 'Жаккард / Премиум ткань'
            else:
                new_fabric_type = 'Рогожка / Универсальная'

        # --- 4. Логика для Свойств ---
        props_list = [p.strip() for p in (new_properties.split(',') if new_properties else []) if p.strip()]
        
        if 'outdoor' in name_lower and 'Водоотталкивание' not in props_list:
            props_list.append('Водоотталкивание')
            props_list.append('Защита от УФ')
        if new_martindale >= 80000 and 'Высокая износостойкость' not in props_list:
            props_list.append('Высокая износостойкость')
        if new_fabric_type in ['Велюр / Микровелюр'] and 'Легкая чистка' not in props_list:
            props_list.append('Легкая чистка')
        if manufacturer == 'Dedar' and 'Премиальное качество' not in props_list:
            props_list.append('Премиальное качество')
            
        new_properties = ", ".join(props_list).strip(", ")

        # --- Обновляем БД если были изменения ---
        if (new_density != density or new_martindale != martindale or 
            new_properties != properties or new_fabric_type != fabric_type):
            cursor.execute("""
                UPDATE fabrics 
                SET density = ?, martindale = ?, properties = ?, fabric_type = ?
                WHERE id = ?
            """, (new_density, new_martindale, new_properties, new_fabric_type, fid))
            updated_count += 1

    conn.commit()
    print(f"База данных успешно обогащена. Обновлено {updated_count} тканей.")

    # --- 5. Экспортируем заново в CSV ---
    dir_name = "данные о тканях для notebooklm"
    os.makedirs(dir_name, exist_ok=True)
    
    query = """
    SELECT 
        name AS 'Название', 
        manufacturer AS 'Производитель', 
        category AS 'Категория', 
        price AS 'Розничная цена', 
        wholesale_price AS 'Оптовая цена', 
        density AS 'Плотность (г/м2)', 
        martindale AS 'Мартиндейл (циклы)', 
        properties AS 'Свойства', 
        fabric_type AS 'Тип ткани',
        product_url AS 'Ссылка на товар'
    FROM fabrics
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()

    csv_path = os.path.join(dir_name, "fabrics_data.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(columns)
        writer.writerows(rows)
        
    print(f"Таблица успешно перезаписана! Файл находится тут: {csv_path}")

if __name__ == "__main__":
    enrich_and_export()
