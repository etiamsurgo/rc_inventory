import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Add new columns to batteries table

try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN type TEXT")
    print("Added column: type")
except:
    print("Column 'type' already exists")

try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN cells INTEGER")
    print("Added column: cells")
except:
    print("Column 'cells' already exists")

conn.commit()
conn.close()

print("Database update complete.")