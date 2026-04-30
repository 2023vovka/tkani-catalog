import sqlite3

def migrate():
    conn = sqlite3.connect('fabrics.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE fabrics ADD COLUMN properties VARCHAR;")
        print("Column 'properties' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Migration error or already applied: {e}")
    conn.commit()

def check_davis():
    conn = sqlite3.connect('fabrics.db')
    cursor = conn.cursor()
    davis_count = cursor.execute("SELECT count(*) FROM fabrics WHERE manufacturer='Davis'").fetchone()[0]
    davis_colors = cursor.execute("SELECT count(*) FROM fabric_colors c JOIN fabrics f ON c.fabric_id=f.id WHERE f.manufacturer='Davis'").fetchone()[0]
    print(f"Davis fabrics: {davis_count}, Davis colors: {davis_colors}")

if __name__ == "__main__":
    migrate()
    check_davis()
