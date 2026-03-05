import sqlite3

conn = sqlite3.connect("inventory.db")
cursor = conn.cursor()

# Aircraft table
cursor.execute("""
CREATE TABLE IF NOT EXISTS aircraft (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    notes TEXT,
    total_hours REAL DEFAULT 0
)
""")

# Batteries table
cursor.execute("""
CREATE TABLE IF NOT EXISTS battery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT,
    capacity TEXT,
    type TEXT,
    cell_count INTEGER,
    cycles INTEGER DEFAULT 0,
    notes TEXT
)
""")

# Flight logs
cursor.execute("""
CREATE TABLE IF NOT EXISTS flight_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aircraft_id INTEGER,
    battery_id INTEGER,
    duration REAL,
    date TEXT,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(id),
    FOREIGN KEY (battery_id) REFERENCES battery(id)
)
""")

# Maintenance logs
cursor.execute("""
CREATE TABLE IF NOT EXISTS maintenance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aircraft_id INTEGER,
    description TEXT,
    date TEXT,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(id)
)
""")

# Owner info
cursor.execute("""
CREATE TABLE IF NOT EXISTS owner (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    ama_number TEXT,
    faa_number TEXT,
    ama_expiration TEXT,
    faa_expiration TEXT
)
""")

conn.commit()
conn.close()

print("Database initialized successfully.")