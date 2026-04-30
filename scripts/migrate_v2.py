import sqlite3

def migrate():
    conn = sqlite3.connect('fabrics.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE fabrics ADD COLUMN product_url VARCHAR;")
        print("Column 'product_url' added to fabrics.")
    except Exception as e: print("error:", e)

    try:
        cursor.execute("ALTER TABLE fabrics ADD COLUMN image_url VARCHAR;")
        print("Column 'image_url' added to fabrics.")
    except Exception as e: print("error:", e)
    
    try:
        cursor.execute("ALTER TABLE fabric_colors ADD COLUMN image_url VARCHAR;")
        print("Column 'image_url' added to fabric_colors.")
    except Exception as e: print("error:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
