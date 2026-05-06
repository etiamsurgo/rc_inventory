import sqlite3
import os

# Use app data folder if available (Electron), otherwise current directory
app_data = os.environ.get('APP_DATA_PATH')
if app_data:
    os.makedirs(app_data, exist_ok=True)
    DB_NAME = os.path.join(app_data, "rc_fleet.db")
else:
    DB_NAME = "rc_fleet.db"


def initialize_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS aircraft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer TEXT,
            model TEXT,
            name TEXT,
            type TEXT,
            default_battery_id INTEGER,
            notes TEXT,
            manual_filename TEXT,
            receipt_filename TEXT,
            picture_filename TEXT
        );

        CREATE TABLE IF NOT EXISTS batteries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            capacity INTEGER,
            cells INTEGER,
            cycles INTEGER DEFAULT 0,
            type TEXT,
            brand TEXT,
            connector TEXT,
            notes TEXT,
            manual_filename TEXT,
            receipt_filename TEXT
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
            notes TEXT,
            manual_filename TEXT,
            receipt_filename TEXT,
            picture_filename TEXT
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

        for table, columns in {
            "aircraft": ["manual_filename", "receipt_filename", "picture_filename"],
            "batteries": ["type", "brand", "connector", "notes", "manual_filename", "receipt_filename", "picture_filename"],
            "items": ["manual_filename", "receipt_filename", "picture_filename"]
        }.items():
            for column in columns:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                except sqlite3.OperationalError:
                    pass

    print("Database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
