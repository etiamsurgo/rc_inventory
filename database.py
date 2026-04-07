import sqlite3
from datetime import datetime

DB_NAME = "rc_fleet.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS aircraft (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            notes TEXT,
            total_minutes INTEGER DEFAULT 0,
            default_battery_id INTEGER
        );
                         
        CREATE TABLE IF NOT EXISTS aircraft_batteries (
            aircraft_id INTEGER,
            battery_id INTEGER,
            PRIMARY KEY (aircraft_id, battery_id)
        );                 

        CREATE TABLE IF NOT EXISTS batteries (
            id INTEGER PRIMARY KEY,
            name TEXT,
            capacity INTEGER,
            cells INTEGER,
            cycles INTEGER DEFAULT 0,
            last_used_date TEXT
        );

        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY,
            aircraft_id INTEGER,
            battery_id INTEGER,
            minutes INTEGER,
            date TEXT
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            brand TEXT,
            model TEXT,
            serial TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY,
            aircraft_id INTEGER,
            description TEXT,
            interval_flights INTEGER,
            last_completed_flights INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pilot_profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            ama_number TEXT,
            ama_expiration TEXT,
            faa_number TEXT,
            faa_expiration TEXT
        );
        """)

# --------------------------------------------------
# Flight Processing Logic
# --------------------------------------------------

def process_flight(aircraft_id, battery_id, minutes):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as db:
        db.execute("""
            INSERT INTO flights (aircraft_id, battery_id, minutes, date)
            VALUES (?, ?, ?, ?)
        """, (aircraft_id, battery_id, minutes, now))

        db.execute("""
            UPDATE aircraft
            SET total_minutes = total_minutes + ?
            WHERE id = ?
        """, (minutes, aircraft_id))

        if battery_id:
            db.execute("""
                UPDATE batteries
                SET cycles = cycles + 1,
                    last_used_date = ?
                WHERE id = ?
            """, (now, battery_id))


# --------------------------------------------------
# Battery Health Helper
# --------------------------------------------------

def get_battery_health(battery):

    warnings = []

    if battery["cycles"] and battery["cycles"] > 150:
        warnings.append("High cycle count")

    if battery["last_used_date"]:
        last_used = datetime.strptime(
            battery["last_used_date"], "%Y-%m-%d %H:%M:%S"
        )

        days_unused = (datetime.now() - last_used).days

        if days_unused > 60:
            warnings.append("Unused > 60 days")

    return warnings