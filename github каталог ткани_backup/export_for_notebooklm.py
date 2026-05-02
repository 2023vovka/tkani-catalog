import sqlite3
import csv
import os

def export_data():
    # 1. Создаем папку
    dir_name = "данные о тканях для notebooklm"
    os.makedirs(dir_name, exist_ok=True)

    # 2. Подключаемся к базе данных
    db_path = 'fabrics.db'
    if not os.path.exists(db_path):
        print(f"Ошибка: База данных {db_path} не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 3. Запрос данных
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
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
    except Exception as e:
        print(f"Ошибка при выполнении запроса к базе данных: {e}")
        return
    finally:
        conn.close()

    # 4. Сохранение в CSV
    csv_path = os.path.join(dir_name, "fabrics_data.csv")
    try:
        # Используем utf-8-sig чтобы Excel или Google Sheets корректно распознали кириллицу
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';') # Точка с запятой часто лучше для Excel
            writer.writerow(columns)
            writer.writerows(rows)
        print(f"Данные успешно экспортированы! Файл сохранен здесь: {csv_path}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")

if __name__ == "__main__":
    export_data()
