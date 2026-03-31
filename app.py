from flask import Flask, render_template, request, redirect
from database import get_db, init_db, process_flight

app = Flask(__name__)

init_db()


@app.route("/")
def home():

    db = get_db()

    pilot = db.execute("SELECT * FROM pilot_profile LIMIT 1").fetchone()
    if pilot is None:
        pilot = {}

    aircraft_count = db.execute("SELECT COUNT(*) FROM aircraft").fetchone()[0]
    item_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    flight_count = db.execute("SELECT COUNT(*) FROM flights").fetchone()[0]

    batteries = db.execute("SELECT * FROM batteries").fetchall()

    top_aircraft = db.execute("""
        SELECT a.name, COALESCE(SUM(f.minutes),0) as total_minutes
        FROM aircraft a
        LEFT JOIN flights f ON a.id = f.aircraft_id
        GROUP BY a.id
        ORDER BY total_minutes DESC
        LIMIT 1
    """).fetchone()

    return render_template(
        "home.html",
        pilot=pilot,
        aircraft_count=aircraft_count,
        item_count=item_count,
        flight_count=flight_count,
        batteries=batteries,
        top_aircraft=top_aircraft
    )


@app.route("/item/<int:item_id>")
def item_detail(item_id):

    db = get_db()

    item = db.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,)
    ).fetchone()

    return render_template("item_detail.html", item=item)


@app.route("/profile", methods=["GET", "POST"])
def profile():

    db = get_db()

    if request.method == "POST":

        db.execute("DELETE FROM pilot_profile")

        db.execute(
            """INSERT INTO pilot_profile 
            (name, ama_number, ama_expiration, faa_number, faa_expiration) 
            VALUES (?,?,?,?,?)""",
            (
                request.form["name"],
                request.form["ama_number"],
                request.form["ama_expiration"],
                request.form["faa_number"],
                request.form["faa_expiration"]
            )
        )

        db.commit()
        return redirect("/")

    pilot = db.execute("SELECT * FROM pilot_profile LIMIT 1").fetchone()

    return render_template("profile.html", pilot=pilot)


@app.route("/aircraft")
def aircraft():

    db = get_db()

    aircraft = db.execute("""
        SELECT a.*, b.name as battery_name
        FROM aircraft a
        LEFT JOIN batteries b ON a.default_battery_id = b.id
    """).fetchall()

    return render_template("aircraft.html", aircraft=aircraft)


@app.route("/aircraft/<int:aircraft_id>")
def aircraft_detail(aircraft_id):

    db = get_db()

    aircraft = db.execute("""
        SELECT a.*, b.name as battery_name
        FROM aircraft a
        LEFT JOIN batteries b ON a.default_battery_id = b.id
        WHERE a.id=?
    """, (aircraft_id,)).fetchone()

    flights = db.execute("""
        SELECT f.*, b.name as battery_name
        FROM flights f
        LEFT JOIN batteries b ON f.battery_id = b.id
        WHERE f.aircraft_id = ?
        ORDER BY f.date DESC
    """, (aircraft_id,)).fetchall()

    compatible_batteries = db.execute("""
        SELECT b.*
        FROM batteries b
        JOIN aircraft_batteries ab
        ON b.id = ab.battery_id
        WHERE ab.aircraft_id = ?
    """, (aircraft_id,)).fetchall()

    return render_template(
        "aircraft_detail.html",
        aircraft=aircraft,
        flights=flights,
        compatible_batteries=compatible_batteries
    )


@app.route("/add_aircraft", methods=["GET", "POST"])
def add_aircraft():

    db = get_db()
    batteries = db.execute("SELECT * FROM batteries").fetchall()

    if request.method == "POST":

        name = request.form["name"]
        type = request.form["type"]
        notes = request.form["notes"]
        default_battery = request.form.get("default_battery")

        usable_batteries = request.form.getlist("usable_batteries[]")

        if default_battery and default_battery not in usable_batteries:
            usable_batteries.append(default_battery)

        cursor = db.execute(
            """
            INSERT INTO aircraft (name, type, notes, default_battery_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                type,
                notes,
                default_battery if default_battery else None
            )
        )

        aircraft_id = cursor.lastrowid

        for battery_id in usable_batteries:
            db.execute(
                "INSERT INTO aircraft_batteries (aircraft_id, battery_id) VALUES (?, ?)",
                (aircraft_id, battery_id)
            )

        db.commit()

        return redirect("/aircraft")

    return render_template("add_aircraft.html", batteries=batteries)


@app.route("/items")
def items():

    db = get_db()
    items = db.execute("SELECT * FROM items").fetchall()

    return render_template("items.html", items=items)


@app.route("/add_item", methods=["GET", "POST"])
def add_item():

    db = get_db()

    if request.method == "POST":

        db.execute(
            "INSERT INTO items (name,category,brand,model,serial,notes) VALUES (?,?,?,?,?,?)",
            (
                request.form["name"],
                request.form["category"],
                request.form["brand"],
                request.form["model"],
                request.form["serial"],
                request.form["notes"]
            )
        )

        db.commit()
        return redirect("/items")

    return render_template("add_item.html")


@app.route("/log_flight", methods=["GET", "POST"])
def log_flight():

    db = get_db()

    aircraft = db.execute("""
        SELECT a.*,
        COALESCE(SUM(f.minutes),0) as total_minutes
        FROM aircraft a
        LEFT JOIN flights f ON a.id = f.aircraft_id
        GROUP BY a.id
        ORDER BY total_minutes DESC
    """).fetchall()

    batteries = db.execute("SELECT * FROM batteries").fetchall()

    quick_minutes = request.args.get("quick")
    aircraft_id = request.args.get("aircraft")

    if quick_minutes and aircraft_id:

        a = db.execute(
            "SELECT * FROM aircraft WHERE id=?",
            (aircraft_id,)
        ).fetchone()

        if a and a["default_battery_id"]:

            minutes = int(quick_minutes)

            process_flight(a["id"], a["default_battery_id"], minutes)

            return redirect("/log_flight")

    if request.method == "POST":

        aircraft_id = request.form["aircraft"]
        battery_id = request.form.get("battery") or None
        minutes = int(request.form["minutes"])

        process_flight(aircraft_id, battery_id, minutes)

        return redirect("/log_flight")

    return render_template(
        "log_flight.html",
        aircraft=aircraft,
        batteries=batteries
    )


@app.route("/analytics")
def analytics():

    db = get_db()

    batteries = db.execute("SELECT name,cycles FROM batteries").fetchall()

    aircraft = db.execute("""
        SELECT aircraft.name,
        SUM(flights.minutes) as minutes
        FROM flights
        JOIN aircraft ON flights.aircraft_id=aircraft.id
        GROUP BY aircraft.id
    """).fetchall()

    return render_template(
        "analytics.html",
        battery_labels=[b["name"] for b in batteries],
        battery_cycles=[b["cycles"] for b in batteries],
        aircraft_labels=[a["name"] for a in aircraft],
        aircraft_minutes=[a["minutes"] for a in aircraft]
    )


if __name__ == "__main__":
    app.run(debug=True)