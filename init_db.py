import sqlite3

conn = sqlite3.connect("rc_fleet.db")
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS aircraft (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer TEXT,
    model TEXT,
    name TEXT,
    type TEXT,
    default_battery_id INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS batteries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    capacity INTEGER,
    cells INTEGER,
    cycles INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS aircraft_batteries (
    aircraft_id INTEGER,
    battery_id INTEGER
);

CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aircraft_id INTEGER,
    battery_id INTEGER,
    date TEXT DEFAULT CURRENT_TIMESTAMP,
    minutes INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    brand TEXT,
    model TEXT,
    serial TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pilot_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    ama_number TEXT,
    ama_expiration TEXT,
    faa_number TEXT,
    faa_expiration TEXT,
    notes TEXT
);
""")

# Add new columns to batteries table if they don't exist
try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN type TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists

try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN brand TEXT")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN connector TEXT")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE batteries ADD COLUMN notes TEXT")
except sqlite3.OperationalError:
    pass

conn.commit()
conn.close()

print("Database initialized successfully.")