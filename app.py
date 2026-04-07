from flask import Flask, render_template, request, redirect
from database import get_db, DB_NAME
import sqlite3
from datetime import datetime
from init_db import initialize_database

app = Flask(__name__)

initialize_database()

sync_done = False


def expiration_info(date_str):
    if not date_str:
        return None

    try:
        exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    today = datetime.now().date()
    days_left = (exp_date - today).days

    if days_left < 0:
        status = "red"
        label = f"Expired {-days_left} day{'s' if -days_left != 1 else ''} ago"
    elif days_left == 0:
        status = "red"
        label = "Expires today"
    elif days_left <= 7:
        status = "red"
        label = f"Expires in {days_left} day{'s' if days_left != 1 else ''}"
    elif days_left <= 30:
        status = "yellow"
        label = f"Expires in {days_left} days"
    else:
        status = "green"
        label = f"Expires in {days_left} days"

    return {
        "status": status,
        "label": label,
        "days_left": days_left
    }


def sync_battery_items():
    with sqlite3.connect(DB_NAME, timeout=5) as conn:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("""
            INSERT INTO batteries (name, capacity, cells, cycles)
            SELECT i.name, NULL, NULL, 0
            FROM items i
            WHERE i.category = 'Battery'
              AND NOT EXISTS (
                  SELECT 1 FROM batteries b WHERE b.name = i.name
              )
        """)


@app.before_request
def initialize_app():
    global sync_done
    if not sync_done:
        sync_battery_items()
        sync_done = True


@app.route("/")
def home():
    db = get_db()

    aircraft_count = db.execute("SELECT COUNT(*) FROM aircraft").fetchone()[0]
    total_minutes = db.execute("SELECT SUM(minutes) FROM flights").fetchone()[0] or 0
    item_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    batteries = db.execute("SELECT * FROM batteries ORDER BY name").fetchall()
    battery_count = len(batteries)

    top_aircraft = db.execute("""
        SELECT a.*, COALESCE(SUM(f.minutes), 0) AS total_minutes
        FROM aircraft a
        LEFT JOIN flights f ON a.id = f.aircraft_id
        GROUP BY a.id
        ORDER BY total_minutes DESC
        LIMIT 1
    """).fetchone()

    pilot = db.execute("SELECT * FROM pilot_profile WHERE id=1").fetchone()

    if pilot:
        pilot = dict(pilot)

        ama_info = expiration_info(pilot["ama_expiration"])
        if ama_info:
            pilot["ama_expiration_label"] = ama_info["label"]
            pilot["ama_expiration_status"] = ama_info["status"]

        faa_info = expiration_info(pilot["faa_expiration"])
        if faa_info:
            pilot["faa_expiration_label"] = faa_info["label"]
            pilot["faa_expiration_status"] = faa_info["status"]

    return render_template(
        "home.html",
        aircraft_count=aircraft_count,
        item_count=item_count,
        battery_count=battery_count,
        top_aircraft=top_aircraft,
        batteries=batteries,
        pilot=pilot
    )


@app.route("/aircraft")
def aircraft():
    db = get_db()

    aircraft = db.execute("""
    SELECT a.*,
           b.name AS battery_name,
           SUM(f.minutes) AS total_minutes,
           COUNT(f.id) AS flight_count
    FROM aircraft a
    LEFT JOIN batteries b ON a.default_battery_id = b.id
    LEFT JOIN flights f ON a.id = f.aircraft_id
    GROUP BY a.id
    ORDER BY a.name
    """).fetchall()

    return render_template("aircraft.html", aircraft=aircraft)


@app.route("/add_aircraft", methods=["GET", "POST"])
def add_aircraft():
    db = get_db()

    batteries = db.execute(
        "SELECT * FROM batteries ORDER BY name"
    ).fetchall()

    if request.method == "POST":

        manufacturer = request.form.get("manufacturer")
        model = request.form.get("model")
        name = request.form.get("name")
        aircraft_type = request.form.get("type")
        default_battery = request.form.get("default_battery")
        notes = request.form.get("notes")

        cursor = db.execute("""
        INSERT INTO aircraft (manufacturer, model, name, type, default_battery_id, notes)
        VALUES (?,?,?,?,?,?)
        """, (
            manufacturer,
            model,
            name,
            aircraft_type,
            default_battery if default_battery else None,
            notes
        ))

        aircraft_id = cursor.lastrowid

        usable_batteries = request.form.getlist("usable_batteries[]")

        if default_battery and default_battery not in usable_batteries:
            usable_batteries.append(default_battery)

        for battery_id in usable_batteries:
            db.execute("""
            INSERT INTO aircraft_batteries (aircraft_id, battery_id)
            VALUES (?,?)
            """, (aircraft_id, battery_id))

        db.commit()

        return redirect("/aircraft")

    return render_template(
        "add_aircraft.html",
        batteries=batteries
    )


@app.route("/edit_aircraft/<int:aircraft_id>", methods=["GET", "POST"])
def edit_aircraft(aircraft_id):

    db = get_db()

    batteries = db.execute(
        "SELECT * FROM batteries ORDER BY name"
    ).fetchall()

    if request.method == "POST":

        manufacturer = request.form.get("manufacturer")
        model = request.form.get("model")
        name = request.form.get("name")
        aircraft_type = request.form.get("type")
        default_battery = request.form.get("default_battery")
        notes = request.form.get("notes")

        db.execute("""
        UPDATE aircraft
        SET manufacturer=?,
            model=?,
            name=?,
            type=?,
            default_battery_id=?,
            notes=?
        WHERE id=?
        """, (
            manufacturer,
            model,
            name,
            aircraft_type,
            default_battery if default_battery else None,
            notes,
            aircraft_id
        ))

        db.execute(
            "DELETE FROM aircraft_batteries WHERE aircraft_id=?",
            (aircraft_id,)
        )

        usable_batteries = request.form.getlist("usable_batteries[]")

        if default_battery and default_battery not in usable_batteries:
            usable_batteries.append(default_battery)

        for battery_id in usable_batteries:
            db.execute("""
            INSERT INTO aircraft_batteries (aircraft_id, battery_id)
            VALUES (?,?)
            """, (aircraft_id, battery_id))

        db.commit()

        return redirect(f"/aircraft/{aircraft_id}")

    aircraft = db.execute(
        "SELECT * FROM aircraft WHERE id=?",
        (aircraft_id,)
    ).fetchone()

    assigned = db.execute("""
    SELECT battery_id
    FROM aircraft_batteries
    WHERE aircraft_id=?
    """, (aircraft_id,)).fetchall()

    assigned_ids = [a["battery_id"] for a in assigned]

    return render_template(
        "edit_aircraft.html",
        aircraft=aircraft,
        batteries=batteries,
        assigned_ids=assigned_ids
    )


@app.route("/delete_aircraft/<int:aircraft_id>", methods=["POST"])
def delete_aircraft(aircraft_id):
    db = get_db()

    db.execute(
        "DELETE FROM flights WHERE aircraft_id=?",
        (aircraft_id,)
    )
    db.execute(
        "DELETE FROM aircraft_batteries WHERE aircraft_id=?",
        (aircraft_id,)
    )
    db.execute(
        "DELETE FROM aircraft WHERE id=?",
        (aircraft_id,)
    )
    db.commit()

    return redirect("/aircraft")


@app.route("/aircraft/<int:aircraft_id>")
def aircraft_detail(aircraft_id):

    db = get_db()

    aircraft = db.execute("""
    SELECT a.*, b.name AS battery_name
    FROM aircraft a
    LEFT JOIN batteries b ON a.default_battery_id = b.id
    WHERE a.id=?
    """, (aircraft_id,)).fetchone()

    flights = db.execute("""
    SELECT f.*, b.name AS battery_name
    FROM flights f
    LEFT JOIN batteries b ON f.battery_id = b.id
    WHERE aircraft_id=?
    ORDER BY date DESC
    """, (aircraft_id,)).fetchall()

    compatible_batteries = db.execute("""
    SELECT b.*
    FROM batteries b
    JOIN aircraft_batteries ab
    ON b.id = ab.battery_id
    WHERE ab.aircraft_id = ?
    """, (aircraft_id,)).fetchall()

    total_minutes = db.execute("""
    SELECT SUM(minutes)
    FROM flights
    WHERE aircraft_id=?
    """, (aircraft_id,)).fetchone()[0] or 0

    aircraft = dict(aircraft)
    aircraft["total_minutes"] = total_minutes

    return render_template(
        "aircraft_detail.html",
        aircraft=aircraft,
        flights=flights,
        compatible_batteries=compatible_batteries
    )


@app.route("/log_flight", methods=["GET", "POST"])
def log_flight():

    db = get_db()

    aircraft = db.execute(
        "SELECT * FROM aircraft ORDER BY name"
    ).fetchall()

    aircraft_id = request.args.get("aircraft") or request.form.get("aircraft")
    selected_aircraft = aircraft_id

    batteries = []
    default_battery_id = None

    if aircraft_id:
        aircraft_row = db.execute(
            "SELECT default_battery_id FROM aircraft WHERE id=?",
            (aircraft_id,)
        ).fetchone()
        if aircraft_row:
            default_battery_id = aircraft_row["default_battery_id"]

        batteries = db.execute("""
        SELECT b.*
        FROM batteries b
        JOIN aircraft_batteries ab
        ON b.id = ab.battery_id
        WHERE ab.aircraft_id = ?
        ORDER BY b.name
        """, (aircraft_id,)).fetchall()

    selected_minutes = request.args.get("minutes")

    if request.method == "POST":

        aircraft_id = request.form["aircraft"]
        battery_id = request.form.get("battery")
        minutes = request.form["minutes"]
        notes = request.form.get("notes")

        db.execute("""
        INSERT INTO flights (aircraft_id, battery_id, minutes, notes)
        VALUES (?,?,?,?)
        """, (
            aircraft_id,
            battery_id if battery_id else None,
            minutes,
            notes
        ))

        if battery_id:
            db.execute(
                "UPDATE batteries SET cycles = cycles + 1 WHERE id=?",
                (battery_id,)
            )

        db.commit()

        return redirect("/")

    return render_template(
        "log_flight.html",
        aircraft=aircraft,
        batteries=batteries,
        selected_aircraft=selected_aircraft,
        default_battery_id=default_battery_id,
        selected_minutes=selected_minutes
    )


@app.route("/items")
def items():
    return redirect("/accessories")


@app.route("/batteries")
def batteries():
    db = get_db()

    batteries_list = db.execute("""
    SELECT *
    FROM batteries
    ORDER BY name
    """).fetchall()

    return render_template("batteries.html", batteries=batteries_list)


@app.route("/accessories")
def accessories():
    db = get_db()

    items = db.execute("""
    SELECT *
    FROM items
    WHERE category != 'Battery'
    ORDER BY category,name
    """).fetchall()

    return render_template("items.html", items=items, page_title="RC Accessories")


@app.route("/add_item", methods=["GET", "POST"])
def add_item():
    category = request.args.get('category', '')
    db = get_db()

    if request.method == "POST":
        category = request.form["category"]

        db.execute("""
        INSERT INTO items (name, category, brand, model, serial, notes)
        VALUES (?,?,?,?,?,?)
        """, (
            request.form["name"],
            category,
            request.form["brand"],
            request.form["model"],
            request.form["serial"],
            request.form["notes"]
        ))

        db.commit()

        return redirect("/accessories")

    return render_template("add_item.html", selected_category=category)


@app.route("/add_battery", methods=["GET", "POST"])
def add_battery():
    if request.method == "POST":
        battery_type = request.form["type"]
        brand = request.form["brand"]
        capacity = request.form["capacity"]
        cells = request.form["cells"]
        connector = request.form["connector"]
        notes = request.form["notes"]
        name = request.form.get("name") or f"{brand} {capacity}mAh {cells}S {battery_type}"

        db = get_db()
        db.execute("""
        INSERT INTO batteries (name, type, brand, capacity, cells, connector, cycles, notes)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (name, battery_type, brand, capacity, cells, connector, notes))

        db.commit()
        return redirect("/batteries")

    return render_template("add_battery.html")


@app.route("/edit_battery/<int:battery_id>", methods=["GET", "POST"])
def edit_battery(battery_id):
    db = get_db()

    if request.method == "POST":
        battery_type = request.form["type"]
        brand = request.form["brand"]
        capacity = request.form["capacity"]
        cells = request.form["cells"]
        connector = request.form["connector"]
        notes = request.form["notes"]
        original_name = request.form.get("original_name")
        name = request.form.get("name")

        if not name or name == original_name:
            name = f"{brand} {capacity}mAh {cells}S {battery_type}"

        db.execute("""
        UPDATE batteries
        SET name=?, type=?, brand=?, capacity=?, cells=?, connector=?, notes=?
        WHERE id=?
        """, (name, battery_type, brand, capacity, cells, connector, notes, battery_id))
        db.commit()
        return redirect("/batteries")

    battery = db.execute(
        "SELECT * FROM batteries WHERE id=?",
        (battery_id,) 
    ).fetchone()

    return render_template("edit_battery.html", battery=battery)


@app.route("/delete_battery/<int:battery_id>", methods=["POST"])
def delete_battery(battery_id):
    db = get_db()
    db.execute("DELETE FROM aircraft_batteries WHERE battery_id=?", (battery_id,))
    db.execute("UPDATE aircraft SET default_battery_id=NULL WHERE default_battery_id=?", (battery_id,))
    db.execute("DELETE FROM flights WHERE battery_id=?", (battery_id,))
    db.execute("DELETE FROM batteries WHERE id=?", (battery_id,))
    db.commit()
    return redirect("/batteries")


@app.route("/battery/<int:battery_id>")
def battery_detail(battery_id):
    db = get_db()

    battery = db.execute(
        "SELECT * FROM batteries WHERE id=?",
        (battery_id,)
    ).fetchone()

    if not battery:
        return redirect("/batteries")

    associated_aircraft = db.execute(
        """
        SELECT a.*
        FROM aircraft a
        JOIN aircraft_batteries ab ON a.id = ab.aircraft_id
        WHERE ab.battery_id = ?
        ORDER BY a.name
        """,
        (battery_id,)
    ).fetchall()

    flights = db.execute(
        """
        SELECT f.*, a.name AS aircraft_name
        FROM flights f
        LEFT JOIN aircraft a ON f.aircraft_id = a.id
        WHERE f.battery_id = ?
        ORDER BY date DESC
        """,
        (battery_id,)
    ).fetchall()

    return render_template(
        "battery_detail.html",
        battery=battery,
        associated_aircraft=associated_aircraft,
        flights=flights
    )


@app.route("/item/<int:item_id>")
def item_detail(item_id):

    db = get_db()

    item = db.execute(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    ).fetchone()

    return render_template(
        "item_detail.html",
        item=item
    )


@app.route("/edit_flight/<int:flight_id>", methods=["GET", "POST"])
def edit_flight(flight_id):
    db = get_db()

    flight = db.execute(
        "SELECT f.*, a.name AS aircraft_name FROM flights f JOIN aircraft a ON f.aircraft_id = a.id WHERE f.id = ?",
        (flight_id,)
    ).fetchone()

    if not flight:
        return redirect("/")

    batteries = db.execute("SELECT * FROM batteries ORDER BY name").fetchall()

    if request.method == "POST":
        battery_id = request.form.get("battery")
        minutes = request.form["minutes"]
        notes = request.form.get("notes")

        db.execute(
            "UPDATE flights SET battery_id=?, minutes=?, notes=? WHERE id=?",
            (battery_id if battery_id else None, minutes, notes, flight_id)
        )
        db.commit()
        return redirect(f"/aircraft/{flight['aircraft_id']}")

    return render_template(
        "edit_flight.html",
        flight=flight,
        batteries=batteries
    )


@app.route("/delete_flight/<int:flight_id>", methods=["POST"])
def delete_flight(flight_id):
    db = get_db()
    flight = db.execute("SELECT * FROM flights WHERE id=?", (flight_id,)).fetchone()
    if flight:
        db.execute("DELETE FROM flights WHERE id=?", (flight_id,))
        db.commit()
        return redirect(f"/aircraft/{flight['aircraft_id']}")
    return redirect("/")


@app.route("/edit_item/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    db = get_db()

    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        brand = request.form["brand"]
        model = request.form["model"]
        serial = request.form["serial"]
        notes = request.form["notes"]

        db.execute("""
        UPDATE items
        SET name=?, category=?, brand=?, model=?, serial=?, notes=?
        WHERE id=?
        """, (name, category, brand, model, serial, notes, item_id))
        db.commit()
        return redirect("/accessories")

    item = db.execute(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    ).fetchone()

    return render_template("edit_item.html", item=item)


@app.route("/delete_item/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    db = get_db()
    db.execute("DELETE FROM items WHERE id=?", (item_id,))
    db.commit()
    return redirect("/accessories")


@app.route("/analytics")
def analytics():

    db = get_db()

    flights = db.execute("""
    SELECT date, COUNT(*) as flights
    FROM flights
    GROUP BY date
    ORDER BY date
    """).fetchall()

    aircraft_usage = db.execute("""
    SELECT a.name, COUNT(f.id) as flights, SUM(f.minutes) as minutes
    FROM aircraft a
    LEFT JOIN flights f
    ON a.id = f.aircraft_id
    GROUP BY a.name
    """).fetchall()

    battery_usage = db.execute("""
    SELECT name, cycles
    FROM batteries
    ORDER BY cycles DESC
    """).fetchall()

    flight_logs = db.execute("""
    SELECT f.id, f.date, f.minutes, f.notes,
           a.name AS aircraft_name,
           b.name AS battery_name
    FROM flights f
    LEFT JOIN aircraft a ON f.aircraft_id = a.id
    LEFT JOIN batteries b ON f.battery_id = b.id
    ORDER BY f.date DESC
    """).fetchall()

    flight_logs = [dict(row) for row in flight_logs]

    # Extract labels and data for charts
    aircraft_labels = [row['name'] for row in aircraft_usage]
    aircraft_minutes = [row['minutes'] or 0 for row in aircraft_usage]
    battery_labels = [row['name'] for row in battery_usage]
    battery_cycles = [row['cycles'] for row in battery_usage]

    return render_template(
        "analytics.html",
        flights=flights,
        aircraft_usage=aircraft_usage,
        aircraft_labels=aircraft_labels,
        aircraft_minutes=aircraft_minutes,
        battery_labels=battery_labels,
        battery_cycles=battery_cycles,
        flight_logs=flight_logs
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():

    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS pilot_profile (
        id INTEGER PRIMARY KEY,
        name TEXT,
        ama_number TEXT,
        ama_expiration TEXT,
        faa_number TEXT,
        faa_expiration TEXT
    )
    """)

    if request.method == "POST":

        db.execute("""
        INSERT INTO pilot_profile (id, name, ama_number, ama_expiration, faa_number, faa_expiration)
        VALUES (1,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            ama_number=excluded.ama_number,
            ama_expiration=excluded.ama_expiration,
            faa_number=excluded.faa_number,
            faa_expiration=excluded.faa_expiration
        """, (
            request.form["name"],
            request.form["ama_number"],
            request.form["ama_expiration"],
            request.form["faa_number"],
            request.form["faa_expiration"]
        ))

        db.commit()

        return redirect("/")

    pilot = db.execute(
        "SELECT * FROM pilot_profile WHERE id=1"
    ).fetchone()

    return render_template(
        "profile.html",
        pilot=pilot
    )


if __name__ == "__main__":
    app.run(debug=True)