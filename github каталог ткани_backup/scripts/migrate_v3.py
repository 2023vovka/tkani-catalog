import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'fabrics.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

def add_column(table, column, col_type):
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"Added {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column} to {table}: {e}")

add_column('fabrics', 'product_url', 'VARCHAR')
add_column('fabrics', 'image_url', 'VARCHAR')
add_column('fabric_colors', 'image_url', 'VARCHAR')

conn.commit()
conn.close()
print("Migration completed.")
