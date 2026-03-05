from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =======================
# MODELS
# =======================

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    category = db.Column(db.String(100))
    notes = db.Column(db.String(300))
    total_minutes = db.Column(db.Integer, default=0)

    maint_logs = db.relationship('MaintenanceLog', backref='aircraft', cascade="all, delete")
    flights = db.relationship('FlightLog', backref='aircraft', cascade="all, delete")

    def formatted_time(self):
        hours = self.total_minutes // 60
        minutes = self.total_minutes % 60
        return f"{hours}h {minutes}m"


class MaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'))
    description = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Battery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100))
    capacity = db.Column(db.String(100))
    type = db.Column(db.String(50))
    cell_count = db.Column(db.Integer)
    cycles = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(300))

    flights = db.relationship('FlightLog', backref='battery', cascade="all, delete")

    def health(self):
        if self.cycles < 100:
            return "Excellent"
        elif self.cycles < 200:
            return "Good"
        elif self.cycles < 300:
            return "Aging"
        else:
            return "Replace Soon"


class FlightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'))
    battery_id = db.Column(db.Integer, db.ForeignKey('battery.id'))
    duration = db.Column(db.Integer)  # minutes
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ama_number = db.Column(db.String(50))
    faa_number = db.Column(db.String(50))
    ama_expiration = db.Column(db.String(20))
    faa_expiration = db.Column(db.String(20))


# =======================
# DASHBOARD
# =======================

@app.route('/')
def dashboard():

    aircraft_count = Aircraft.query.count()
    battery_count = Battery.query.count()
    flight_count = FlightLog.query.count()

    total_minutes = db.session.query(db.func.sum(Aircraft.total_minutes)).scalar() or 0
    hours = total_minutes // 60
    minutes = total_minutes % 60

    owner = Owner.query.first()

    return render_template(
        "home.html",
        aircraft_count=aircraft_count,
        battery_count=battery_count,
        flight_count=flight_count,
        total_time=f"{hours}h {minutes}m",
        owner=owner
    )


# =======================
# AIRCRAFT
# =======================

@app.route('/aircraft')
def aircraft():

    aircraft = Aircraft.query.order_by(Aircraft.name.asc()).all()
    batteries = Battery.query.all()

    return render_template("aircraft.html", aircraft=aircraft, batteries=batteries)


@app.route('/add_aircraft', methods=['POST'])
def add_aircraft():

    new_aircraft = Aircraft(
        name=request.form['name'],
        brand=request.form['brand'],
        category=request.form['category'],
        notes=request.form['notes']
    )

    db.session.add(new_aircraft)
    db.session.commit()

    return redirect(url_for('aircraft'))


@app.route('/delete_aircraft/<int:id>')
def delete_aircraft(id):

    aircraft = Aircraft.query.get_or_404(id)
    db.session.delete(aircraft)
    db.session.commit()

    return redirect(url_for('aircraft'))


# =======================
# FLIGHT LOGGING
# =======================

@app.route('/add_flight/<int:aircraft_id>', methods=['POST'])
def add_flight(aircraft_id):

    minutes = int(request.form['minutes'])
    battery_id = int(request.form['battery_id'])

    flight = FlightLog(
        aircraft_id=aircraft_id,
        battery_id=battery_id,
        duration=minutes
    )

    db.session.add(flight)

    aircraft = Aircraft.query.get(aircraft_id)
    aircraft.total_minutes += minutes

    battery = Battery.query.get(battery_id)
    battery.cycles += 1

    db.session.commit()

    return redirect(url_for('aircraft'))


# =======================
# QUICK FLIGHT LOGGER
# =======================

@app.route('/log_flight')
def log_flight():

    aircraft = Aircraft.query.all()
    batteries = Battery.query.all()

    return render_template("log_flight.html", aircraft=aircraft, batteries=batteries)


@app.route('/quick_log', methods=['POST'])
def quick_log():

    aircraft_id = int(request.form['aircraft_id'])
    battery_id = int(request.form['battery_id'])
    minutes = int(request.form['minutes'])

    flight = FlightLog(
        aircraft_id=aircraft_id,
        battery_id=battery_id,
        duration=minutes
    )

    db.session.add(flight)

    aircraft = Aircraft.query.get(aircraft_id)
    aircraft.total_minutes += minutes

    battery = Battery.query.get(battery_id)
    battery.cycles += 1

    db.session.commit()

    return redirect(url_for('dashboard'))


# =======================
# FLIGHT HISTORY
# =======================

@app.route('/flight_history/<int:aircraft_id>')
def flight_history(aircraft_id):

    aircraft = Aircraft.query.get_or_404(aircraft_id)

    flights = FlightLog.query.filter_by(
        aircraft_id=aircraft_id
    ).order_by(
        FlightLog.date.desc()
    ).all()

    return render_template(
        "flight_history.html",
        aircraft=aircraft,
        flights=flights
    )


# =======================
# BATTERIES
# =======================

@app.route('/batteries')
def batteries():

    batteries = Battery.query.order_by(Battery.cycles.desc()).all()

    return render_template("batteries.html", batteries=batteries)


@app.route('/add_battery', methods=['POST'])
def add_battery():

    battery = Battery(
        brand=request.form['brand'],
        capacity=request.form['capacity'],
        type=request.form['type'],
        cell_count=request.form['cell_count'],
        notes=request.form['notes']
    )

    db.session.add(battery)
    db.session.commit()

    return redirect(url_for('batteries'))


@app.route('/delete_battery/<int:id>')
def delete_battery(id):

    battery = Battery.query.get_or_404(id)
    db.session.delete(battery)
    db.session.commit()

    return redirect(url_for('batteries'))


# =======================
# CSV EXPORT
# =======================

@app.route('/export_flights')
def export_flights():

    flights = FlightLog.query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Aircraft", "Battery", "Minutes", "Date"])

    for f in flights:

        writer.writerow([
            f.aircraft.name,
            f.battery.brand,
            f.duration,
            f.date
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="flight_logs.csv"
    )


# =======================
# OWNER + ADMIN
# =======================

@app.route("/owner")
def owner():
    return render_template("owner.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# =======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)