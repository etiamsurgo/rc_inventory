from flask import Flask, render_template, request, redirect
from database import get_db, DB_NAME
import sqlite3

app = Flask(__name__)

sync_done = False

def sync_battery_items():
    conn = sqlite3.connect(DB_NAME, timeout=5)
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
    conn.commit()
    conn.close()


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
    flight_count = db.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    total_minutes = db.execute("SELECT SUM(minutes) FROM flights").fetchone()[0] or 0
    item_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    batteries = db.execute("SELECT * FROM batteries ORDER BY name").fetchall()

    top_aircraft = db.execute("""
        SELECT a.*, COALESCE(SUM(f.minutes), 0) AS total_minutes
        FROM aircraft a
        LEFT JOIN flights f ON a.id = f.aircraft_id
        GROUP BY a.id
        ORDER BY total_minutes DESC
        LIMIT 1
    """).fetchone()

    pilot = db.execute("SELECT * FROM pilot_profile WHERE id=1").fetchone()

    return render_template(
        "home.html",
        aircraft_count=aircraft_count,
        item_count=item_count,
        flight_count=flight_count,
        top_aircraft=top_aircraft,
        batteries=batteries,
        pilot=pilot
    )


@app.route("/aircraft")
def aircraft():
    db = get_db()

    aircraft = db.execute("""
    SELECT a.*,
           SUM(f.minutes) AS total_minutes,
           COUNT(f.id) AS flight_count
    FROM aircraft a
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

    batteries = []

    if aircraft_id:
        batteries = db.execute("""
        SELECT b.*
        FROM batteries b
        JOIN aircraft_batteries ab
        ON b.id = ab.battery_id
        WHERE ab.aircraft_id = ?
        ORDER BY b.name
        """, (aircraft_id,)).fetchall()

    quick = request.args.get("quick")

    if quick and aircraft_id:

        db.execute("""
        INSERT INTO flights (aircraft_id, minutes)
        VALUES (?,?)
        """, (aircraft_id, quick))

        db.commit()

        return redirect(f"/aircraft/{aircraft_id}")

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
        selected_aircraft=aircraft_id
    )


@app.route("/items")
def items():
    db = get_db()

    items = db.execute("""
    SELECT *
    FROM items
    ORDER BY category,name
    """).fetchall()

    return render_template("items.html", items=items)


@app.route("/add_item", methods=["GET", "POST"])
def add_item():

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

        if category == "Battery":
            db.execute("""
            INSERT INTO batteries (name, capacity, cells, cycles)
            VALUES (?, NULL, NULL, 0)
            """, (request.form["name"],))

        db.commit()

        return redirect("/items")

    return render_template("add_item.html")


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
    SELECT a.name, COUNT(f.id) as flights
    FROM aircraft a
    LEFT JOIN flights f
    ON a.id = f.aircraft_id
    GROUP BY a.name
    """).fetchall()

    return render_template(
        "analytics.html",
        flights=flights,
        aircraft_usage=aircraft_usage
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