import pdfplumber
import pandas as pd
import re
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEDAR_PDF = os.path.join(ROOT_DIR, "Dedar Pricelist 2026 .pdf")
MARIAFLORA_PDF = os.path.join(ROOT_DIR, "MariaFlora Pricelist 2026.pdf")
OUTPUT_EXCEL = os.path.join(ROOT_DIR, "Новые_Ткани_Каталог.xlsx")

def clean_name(raw_name):
    if not raw_name: return ""
    clean = re.split(r' col\.| Coord:| All', str(raw_name))[0]
    return clean.strip().replace('\n', ' ')

def extract_dedar_martindale(pdf_path):
    print("[*] Чтение таблиц Мартиндейла Dedar (стр 20, 73, 74, 79)...")
    martindales = {}
    if not os.path.exists(pdf_path): return martindales
    
    target_pages = [19, 72, 73, 78] # Индексы с 0 (20->19, 73->72...)
    with pdfplumber.open(pdf_path) as pdf:
        for p_idx in target_pages:
            if p_idx < len(pdf.pages):
                tables = pdf.pages[p_idx].extract_tables()
                for table in tables:
                    for row in table:
                        if len(row) >= 2 and row[0] and row[1]:
                            name = clean_name(row[0])
                            # Ищем цифры в строке с мартиндейлом
                            m_match = re.search(r'(\d{2,3}[\s.]?\d{3})', str(row[1]))
                            if m_match:
                                try:
                                    martindales[name] = int(re.sub(r'[^\d]', '', m_match.group(1)))
                                except: pass
    return martindales

def parse_dedar(pdf_path):
    print(f"[*] Чтение Dedar PDF: {pdf_path}")
    data = []
    if not os.path.exists(pdf_path):
        print("[-] Файл Dedar не найден!")
        return data
        
    martindales = extract_dedar_martindale(pdf_path)
        
    with pdfplumber.open(pdf_path) as pdf:
        # Основной каталог обычно с 15 страницы
        for i, page in enumerate(pdf.pages[15:100]): 
            tables = page.extract_tables()
            for table in tables:
                for row in table[1:]:
                    if row and len(row) >= 3 and row[1]:
                        name = clean_name(row[1])
                        code = str(row[0]).strip() if row[0] else ""
                        if len(name) < 3 or "Description" in name or "Item" in name:
                            continue
                            
                        # Объединяем имя и артикул
                        full_name = f"{name} {code}".strip()
                            
                        try:
                            price_str = str(row[2]).replace(',', '.').replace('€', '').strip()
                            price_match = re.search(r'(\d+\.\d+)', price_str)
                            price = float(price_match.group(1)) if price_match else float(price_str)
                        except: price = 0.0
                            
                        # Ищем Мартиндейл в словаре
                        martindale_val = ""
                        for m_name, m_val in martindales.items():
                            if m_name in name or name in m_name:
                                martindale_val = m_val
                                break
                                
                        data.append({
                            "Наименование": full_name,
                            "Производитель": "Dedar",
                            "Категория": "Премиум",
                            "Цена*": price,
                            "Свойства": "",
                            "Плотность": "",
                            "Мартиндейл": martindale_val
                        })
    return data

def parse_mariaflora(pdf_path):
    print(f"[*] Чтение MariaFlora PDF: {pdf_path}")
    data = []
    if not os.path.exists(pdf_path):
        print("[-] Файл MariaFlora не найден!")
        return data
        
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages): 
            tables = page.extract_tables()
            for table in tables:
                for row in table[1:]:
                    if row and len(row) >= 3 and row[0]:
                        name = clean_name(row[0])
                        # Предположительно 2 колонка - это артикул, либо все в первой
                        if len(name) < 3 or "Item" in name:
                            continue
                            
                        try:
                            price_str = str(row[1] if len(row) > 1 else row[-1]).replace(',', '.').replace('€', '').strip()
                            price_match = re.search(r'(\d+\.\d+)', price_str)
                            price = float(price_match.group(1)) if price_match else float(price_str)
                        except: price = 0.0
                            
                        # Свойства (по ТЗ: "Водоотталкивание, Уличная" переводим в наши иконки)
                        props = "💧 ✨"
                        
                        # Ищем Мартиндейл прямо в строке
                        row_text = " ".join([str(c) for c in row if c])
                        m_match = re.search(r'(\d{2,3}[\s.]?\d{3})', row_text)
                        martindale_val = ""
                        if m_match:
                            try: martindale_val = int(re.sub(r'[^\d]', '', m_match.group(1)))
                            except: pass
                            
                        data.append({
                            "Наименование": name,
                            "Производитель": "Mariaflora",
                            "Категория": "Премиум",
                            "Цена*": price,
                            "Свойства": props,
                            "Плотность": "",
                            "Мартиндейл": martindale_val
                        })
    return data

def main():
    dedar_data = parse_dedar(DEDAR_PDF)
    maria_data = parse_mariaflora(MARIAFLORA_PDF)
    all_data = dedar_data + maria_data
    
    if not all_data:
        print("[-] Не удалось собрать данные.")
        return
        
    df = pd.DataFrame(all_data, columns=["Наименование", "Производитель", "Категория", "Цена*", "Свойства", "Плотность", "Мартиндейл"])
    df.drop_duplicates(subset=["Наименование", "Производитель"], inplace=True)
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"[+] Готово! Извлечено {len(df)} тканей. Сохранено в {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
