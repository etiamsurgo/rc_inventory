from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -----------------------
# MODELS
# -----------------------

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(100))
    default_battery_id = db.Column(db.Integer, db.ForeignKey("battery.id"), nullable=True)


class Battery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100))
    capacity = db.Column(db.Integer)
    cells = db.Column(db.Integer)
    cycles = db.Column(db.Integer, default=0)


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey("aircraft.id"))
    battery_id = db.Column(db.Integer, db.ForeignKey("battery.id"))
    duration_minutes = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    aircraft = db.relationship("Aircraft")
    battery = db.relationship("Battery")


# -----------------------
# HELPERS
# -----------------------

def format_hours(minutes):

    hours = minutes // 60
    mins = minutes % 60

    return f"{hours}h {mins}m"


app.jinja_env.globals.update(format_hours=format_hours)


# -----------------------
# HOME
# -----------------------

@app.route("/")
def index():

    aircraft = Aircraft.query.all()
    batteries = Battery.query.all()

    flights = Flight.query.order_by(Flight.date.desc()).limit(10).all()

    aircraft_count = len(aircraft)
    battery_count = len(batteries)
    flight_count = Flight.query.count()

    total_minutes = sum(f.duration_minutes for f in Flight.query.all())

    # aircraft totals
    for a in aircraft:
        minutes = sum(
            f.duration_minutes for f in Flight.query.filter_by(aircraft_id=a.id).all()
        )
        a.total_minutes = minutes

    # battery warnings
    for b in batteries:
        if b.cycles >= 200:
            b.warning = "⚠ Replace Soon"
        elif b.cycles >= 150:
            b.warning = "⚠ Aging"
        else:
            b.warning = ""

    return render_template(
        "index.html",
        aircraft=aircraft,
        batteries=batteries,
        flights=flights,
        aircraft_count=aircraft_count,
        battery_count=battery_count,
        flight_count=flight_count,
        total_minutes=total_minutes,
    )


# -----------------------
# ADD AIRCRAFT
# -----------------------

@app.route("/add_aircraft", methods=["GET", "POST"])
def add_aircraft():

    batteries = Battery.query.all()

    if request.method == "POST":

        name = request.form["name"]
        type = request.form["type"]
        default_battery_id = request.form.get("default_battery")

        aircraft = Aircraft(
            name=name,
            type=type,
            default_battery_id=default_battery_id if default_battery_id else None,
        )

        db.session.add(aircraft)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("add_aircraft.html", batteries=batteries)


# -----------------------
# ADD BATTERY
# -----------------------

@app.route("/add_battery", methods=["GET", "POST"])
def add_battery():

    if request.method == "POST":

        brand = request.form["brand"]
        capacity = request.form["capacity"]
        cells = request.form["cells"]

        battery = Battery(
            brand=brand,
            capacity=int(capacity),
            cells=int(cells),
            cycles=0,
        )

        db.session.add(battery)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("add_battery.html")


# -----------------------
# LOG FLIGHT
# -----------------------

@app.route("/log_flight", methods=["GET", "POST"])
def log_flight():

    aircraft = Aircraft.query.all()
    batteries = Battery.query.all()

    if request.method == "POST":

        aircraft_id = request.form["aircraft_id"]
        battery_id = request.form["battery_id"]
        duration = request.form["duration"]

        flight = Flight(
            aircraft_id=int(aircraft_id),
            battery_id=int(battery_id),
            duration_minutes=int(duration),
        )

        db.session.add(flight)

        battery = Battery.query.get(battery_id)
        battery.cycles += 1

        db.session.commit()

        return redirect(url_for("index"))

    return render_template(
        "log_flight.html",
        aircraft=aircraft,
        batteries=batteries,
    )


# -----------------------
# QUICK FLIGHT
# -----------------------

@app.route("/quick_flight/<int:aircraft_id>/<int:duration>")
def quick_flight(aircraft_id, duration):

    aircraft = Aircraft.query.get_or_404(aircraft_id)

    battery_id = aircraft.default_battery_id

    if not battery_id:
        return redirect(url_for("log_flight"))

    flight = Flight(
        aircraft_id=aircraft_id,
        battery_id=battery_id,
        duration_minutes=duration,
    )

    db.session.add(flight)

    battery = Battery.query.get(battery_id)
    battery.cycles += 1

    db.session.commit()

    return redirect(url_for("index"))


# -----------------------
# AIRCRAFT HISTORY
# -----------------------

@app.route("/aircraft/<int:aircraft_id>")
def aircraft_history(aircraft_id):

    aircraft = Aircraft.query.get_or_404(aircraft_id)

    flights = Flight.query.filter_by(aircraft_id=aircraft_id).order_by(
        Flight.date.desc()
    )

    total_minutes = sum(f.duration_minutes for f in flights)

    return render_template(
        "aircraft_history.html",
        aircraft=aircraft,
        flights=flights,
        total_minutes=total_minutes,
    )


# -----------------------
# ANALYTICS
# -----------------------

@app.route("/analytics")
def analytics():

    batteries = Battery.query.all()
    aircraft = Aircraft.query.all()

    battery_labels = [f"{b.brand} {b.capacity}" for b in batteries]
    battery_cycles = [b.cycles for b in batteries]

    aircraft_labels = []
    aircraft_minutes = []

    for a in aircraft:

        minutes = sum(
            f.duration_minutes for f in Flight.query.filter_by(aircraft_id=a.id).all()
        )

        aircraft_labels.append(a.name)
        aircraft_minutes.append(minutes)

    return render_template(
        "analytics.html",
        battery_labels=battery_labels,
        battery_cycles=battery_cycles,
        aircraft_labels=aircraft_labels,
        aircraft_minutes=aircraft_minutes,
    )


# -----------------------

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)