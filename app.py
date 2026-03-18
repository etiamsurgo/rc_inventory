from flask import Flask, render_template, request, redirect
from database import get_db, init_db

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

    return render_template(
        "home.html",
        pilot=pilot,
        aircraft_count=aircraft_count,
        item_count=item_count,
        flight_count=flight_count,
        batteries=batteries
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():

    db = get_db()

    if request.method == "POST":

        db.execute("DELETE FROM pilot_profile")

        db.execute(
            "INSERT INTO pilot_profile (name, ama_number, ama_expiration, faa_number, faa_expiration) VALUES (?,?,?,?,?)",
            (
                request.form["name"],
                request.form["ama"],
                request.form["ama_exp"],
                request.form["faa"],
                request.form["faa_exp"]
            )
        )

        db.commit()
        return redirect("/")

    pilot = db.execute("SELECT * FROM pilot_profile LIMIT 1").fetchone()

    return render_template("profile.html", pilot=pilot)


@app.route("/aircraft")
def aircraft():

    db = get_db()
    aircraft = db.execute("SELECT * FROM aircraft").fetchall()

    return render_template("aircraft.html", aircraft=aircraft)


@app.route("/add_aircraft", methods=["GET", "POST"])
def add_aircraft():

    db = get_db()

    if request.method == "POST":

        db.execute(
            "INSERT INTO aircraft (name,type,notes) VALUES (?,?,?)",
            (
                request.form["name"],
                request.form["type"],
                request.form["notes"]
            )
        )

        db.commit()
        return redirect("/aircraft")

    return render_template("add_aircraft.html")


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


# ✅ CLEAN LOG FLIGHT ROUTE
@app.route("/log_flight", methods=["GET", "POST"])
def log_flight():

    db = get_db()

    aircraft = db.execute("SELECT * FROM aircraft").fetchall()
    batteries = db.execute("SELECT * FROM batteries").fetchall()

    # QUICK LOG
    quick_minutes = request.args.get("quick")
    aircraft_id = request.args.get("aircraft")

    if quick_minutes and aircraft_id:

        a = db.execute(
            "SELECT * FROM aircraft WHERE id=?",
            (aircraft_id,)
        ).fetchone()

        if a and a["default_battery_id"]:

            b = db.execute(
                "SELECT * FROM batteries WHERE id=?",
                (a["default_battery_id"],)
            ).fetchone()

            if b:
                minutes = int(quick_minutes)

                db.execute(
                    "INSERT INTO flights (aircraft_id, battery_id, minutes) VALUES (?,?,?)",
                    (a["id"], b["id"], minutes)
                )

                db.execute(
                    "UPDATE aircraft SET total_minutes = total_minutes + ? WHERE id=?",
                    (minutes, a["id"])
                )

                db.execute(
                    "UPDATE batteries SET cycles = cycles + 1 WHERE id=?",
                    (b["id"],)
                )

                db.commit()

                return redirect("/log_flight")

    # NORMAL FORM
    if request.method == "POST":

        aircraft_id = request.form["aircraft"]
        battery_id = request.form["battery"]
        minutes = int(request.form["minutes"])

        db.execute(
            "INSERT INTO flights (aircraft_id, battery_id, minutes) VALUES (?,?,?)",
            (aircraft_id, battery_id, minutes)
        )

        db.execute(
            "UPDATE aircraft SET total_minutes = total_minutes + ? WHERE id=?",
            (minutes, aircraft_id)
        )

        db.execute(
            "UPDATE batteries SET cycles = cycles + 1 WHERE id=?",
            (battery_id,)
        )

        db.commit()

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