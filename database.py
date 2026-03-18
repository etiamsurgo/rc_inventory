import sqlite3

DB_NAME = "rc_fleet.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    db = get_db()

    db.executescript("""

CREATE TABLE IF NOT EXISTS pilot_profile (
id INTEGER PRIMARY KEY,
name TEXT,
ama_number TEXT,
ama_expiration TEXT,
faa_number TEXT,
faa_expiration TEXT
);

CREATE TABLE IF NOT EXISTS aircraft (
id INTEGER PRIMARY KEY,
name TEXT,
type TEXT,
notes TEXT
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

CREATE TABLE IF NOT EXISTS batteries (
id INTEGER PRIMARY KEY,
name TEXT,
capacity INTEGER,
cells INTEGER,
cycles INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS flights (
id INTEGER PRIMARY KEY,
aircraft_id INTEGER,
battery_id INTEGER,
minutes INTEGER,
date TEXT
);

CREATE TABLE IF NOT EXISTS maintenance (
id INTEGER PRIMARY KEY,
aircraft_id INTEGER,
description TEXT,
interval_flights INTEGER,
last_done INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS aircraft_components (
id INTEGER PRIMARY KEY,
aircraft_id INTEGER,
item_id INTEGER
);

""")

    db.commit()